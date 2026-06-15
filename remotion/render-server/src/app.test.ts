import request from 'supertest';
import {beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
  fetchVideo: vi.fn(),
  updateVideo: vi.fn(),
  renderVideoJob: vi.fn(),
}));

vi.mock('./supabase', () => ({
  fetchVideo: mocks.fetchVideo,
  updateVideo: mocks.updateVideo,
}));
vi.mock('./render', () => ({
  renderVideoJob: mocks.renderVideoJob,
}));

import {createApp} from './app';

const app = createApp();

const assetsReadyRow = {
  id: 'vid-1',
  status: 'assets_ready',
  kind: 'generated',
  template: 'explainer',
  topic: 'Topic',
  script_json: {},
  asset_urls: {},
  enhancement_json: null,
};

const enhancedReadyRow = {
  id: 'enh-1',
  status: 'assets_ready',
  kind: 'enhanced',
  template: null,
  topic: 'My build',
  script_json: null,
  asset_urls: null,
  enhancement_json: {
    source_video_url: 'https://x/v.mp4',
    source_duration_s: 10,
    overlays: [],
    platform_captions: {youtube: 'x'},
    hashtags: {youtube: ['#x']},
  },
};

beforeEach(() => {
  vi.resetAllMocks();
});

describe('GET /healthz', () => {
  it('returns ok', async () => {
    const res = await request(app).get('/healthz');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ok: true});
  });
});

describe('POST /render', () => {
  it('400 when video_id missing', async () => {
    const res = await request(app).post('/render').send({});
    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/video_id/);
  });

  it('404 when video not found', async () => {
    mocks.fetchVideo.mockResolvedValue(null);
    const res = await request(app).post('/render').send({video_id: 'nope'});
    expect(res.status).toBe(404);
  });

  it('409 when video is not assets_ready', async () => {
    mocks.fetchVideo.mockResolvedValue({...assetsReadyRow, status: 'scripted'});
    const res = await request(app).post('/render').send({video_id: 'vid-1'});
    expect(res.status).toBe(409);
    expect(res.body.error).toMatch(/assets_ready/);
  });

  it('422 when template is missing or unknown (nullable DB column)', async () => {
    mocks.fetchVideo.mockResolvedValue({...assetsReadyRow, template: null});
    const res = await request(app).post('/render').send({video_id: 'vid-1'});
    expect(res.status).toBe(422);
    expect(res.body.error).toMatch(/template/);
    expect(mocks.renderVideoJob).not.toHaveBeenCalled();
  });

  it('renders, updates row to qa_pending, returns urls', async () => {
    mocks.fetchVideo.mockResolvedValue(assetsReadyRow);
    mocks.renderVideoJob.mockResolvedValue({
      renderUrl: 'https://x/renders/vid-1.mp4',
      thumbnailUrl: 'https://x/renders/vid-1.png',
    });
    const res = await request(app).post('/render').send({video_id: 'vid-1'});
    expect(res.status).toBe(200);
    expect(res.body).toEqual({
      ok: true,
      render_url: 'https://x/renders/vid-1.mp4',
      thumbnail_url: 'https://x/renders/vid-1.png',
    });
    expect(mocks.updateVideo).toHaveBeenCalledWith('vid-1', {
      status: 'qa_pending',
      render_url: 'https://x/renders/vid-1.mp4',
      thumbnail_url: 'https://x/renders/vid-1.png',
    });
  });

  it('500 + row untouched when render fails', async () => {
    mocks.fetchVideo.mockResolvedValue(assetsReadyRow);
    mocks.renderVideoJob.mockRejectedValue(new Error('chromium crashed'));
    const res = await request(app).post('/render').send({video_id: 'vid-1'});
    expect(res.status).toBe(500);
    expect(mocks.updateVideo).not.toHaveBeenCalled();
  });

  it('renders an enhanced (kind=enhanced) row even though template is null', async () => {
    mocks.fetchVideo.mockResolvedValue(enhancedReadyRow);
    mocks.renderVideoJob.mockResolvedValue({
      renderUrl: 'https://x/renders/enh-1.mp4',
      thumbnailUrl: 'https://x/renders/enh-1.png',
    });
    const res = await request(app).post('/render').send({video_id: 'enh-1'});
    expect(res.status).toBe(200);
    expect(mocks.updateVideo).toHaveBeenCalledWith('enh-1', {
      status: 'qa_pending',
      render_url: 'https://x/renders/enh-1.mp4',
      thumbnail_url: 'https://x/renders/enh-1.png',
    });
  });
});
