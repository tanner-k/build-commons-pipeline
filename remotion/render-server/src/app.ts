import express, {type Express} from 'express';
import {renderVideoJob} from './render';
import {fetchVideo, updateVideo} from './supabase';

// Mirrors COMPOSITION_BY_TEMPLATE in render.ts. videos.template is nullable in
// the DB, so reject unknown/missing templates here with a clear 422 instead of
// letting selectComposition(undefined) throw opaquely mid-render.
const RENDERABLE_TEMPLATES = new Set(['explainer', 'tutorial', 'listicle', 'comparison']);

export const createApp = (): Express => {
  const app = express();
  app.use(express.json());

  app.get('/healthz', (_req, res) => {
    res.json({ok: true});
  });

  app.post('/render', async (req, res) => {
    const videoId = req.body?.video_id;
    if (typeof videoId !== 'string' || videoId.length === 0) {
      res.status(400).json({error: 'video_id (string) is required'});
      return;
    }
    try {
      const video = await fetchVideo(videoId);
      if (!video) {
        res.status(404).json({error: `video ${videoId} not found`});
        return;
      }
      if (video.status !== 'assets_ready') {
        res.status(409).json({
          error: `video ${videoId} is '${video.status}', expected 'assets_ready'`,
        });
        return;
      }
      if (!RENDERABLE_TEMPLATES.has(video.template)) {
        res.status(422).json({
          error: `video ${videoId} has unknown/missing template '${video.template}'`,
        });
        return;
      }
      const {renderUrl, thumbnailUrl} = await renderVideoJob(video);
      await updateVideo(videoId, {
        status: 'qa_pending',
        render_url: renderUrl,
        thumbnail_url: thumbnailUrl,
      });
      res.json({ok: true, render_url: renderUrl, thumbnail_url: thumbnailUrl});
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.error(`[render] ${videoId} failed:`, message);
      res.status(500).json({error: message});
    }
  });

  return app;
};
