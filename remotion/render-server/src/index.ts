import {config} from './config';
import {createApp} from './app';

const app = createApp();
app.listen(config.port, () => {
  console.log(`render server listening on :${config.port}`);
});
