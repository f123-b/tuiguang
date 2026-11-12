// Launch the unmodified real product in a NEW synthetic, network-blocked profile.
// Never point this at personal user data or copy secrets into the profile.
const {app, session} = require('electron');
const path = require('node:path');
const root = path.resolve(__dirname, '../../..');
process.env.INTERVIEW_COPILOT_PREVIEW_USER_DATA = path.join(root, '.data/short-drama-49/product-profile');
process.env.INTERVIEW_COPILOT_TEST_DATA_PATH = path.join(root, '.data/short-drama-49/product-data');
process.env.INTERVIEW_COPILOT_DISABLE_GPU = '1';
app.commandLine.appendSwitch('remote-debugging-port', '9349');
app.commandLine.appendSwitch('disable-gpu');
app.commandLine.appendSwitch('disable-background-networking');
app.on('browser-window-created', (_event, win) => {
  win.once('ready-to-show', () => {win.setBounds({x:0,y:0,width:2560,height:1440});});
});
app.whenReady().then(() => {
  session.defaultSession.webRequest.onBeforeRequest({urls: ['http://*/*', 'https://*/*']}, (_details, callback) => callback({cancel:true}));
});
require('D:/电脑面试/apps/desktop/out/main/index.js');
