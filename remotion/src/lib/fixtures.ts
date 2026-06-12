import sampleAssets from '../../../schemas/fixtures/sample_assets.json';
import sampleScript from '../../../schemas/fixtures/sample_video_script.json';
import {videoAssetsSchema, videoScriptSchema} from '../types/video-script';

export const SAMPLE_SCRIPT = videoScriptSchema.parse(sampleScript);
export const SAMPLE_ASSETS = videoAssetsSchema.parse(sampleAssets);
