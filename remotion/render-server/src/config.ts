const required = (name: string): string => {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
};

export const config = {
  port: Number(process.env.RENDER_SERVER_PORT ?? 3333),
  rendersBucket: process.env.RENDERS_BUCKET ?? 'renders',
  // Lazy so tests never need real credentials.
  supabaseUrl: () => required('SUPABASE_URL'),
  supabaseServiceRoleKey: () => required('SUPABASE_SERVICE_ROLE_KEY'),
};
