import {createClient, type SupabaseClient} from '@supabase/supabase-js';
import {config} from './config';

export type VideoRow = {
  id: string;
  status: string;
  template: 'explainer' | 'tutorial' | 'listicle' | 'comparison';
  topic: string;
  script_json: unknown;
  asset_urls: unknown;
};

let client: SupabaseClient | null = null;
const getClient = (): SupabaseClient => {
  client ??= createClient(config.supabaseUrl(), config.supabaseServiceRoleKey());
  return client;
};

export const fetchVideo = async (id: string): Promise<VideoRow | null> => {
  const {data, error} = await getClient()
    .from('videos')
    .select('id,status,template,topic,script_json,asset_urls')
    .eq('id', id)
    .maybeSingle();
  if (error) throw new Error(`fetchVideo(${id}): ${error.message}`);
  return data as VideoRow | null;
};

export const updateVideo = async (
  id: string,
  patch: Record<string, unknown>,
): Promise<void> => {
  const {error} = await getClient().from('videos').update(patch).eq('id', id);
  if (error) throw new Error(`updateVideo(${id}): ${error.message}`);
};

export const uploadRender = async (
  path: string,
  body: Buffer,
  contentType: string,
): Promise<string> => {
  const supabase = getClient();
  const {error} = await supabase.storage
    .from(config.rendersBucket)
    .upload(path, body, {contentType, upsert: true});
  if (error) throw new Error(`uploadRender(${path}): ${error.message}`);
  return supabase.storage.from(config.rendersBucket).getPublicUrl(path).data.publicUrl;
};
