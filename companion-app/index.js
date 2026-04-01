/**
 * @format
 */

import { AppRegistry } from 'react-native';
import { registerBackgroundHandler } from './src/notifications/backgroundHandler';
import App from './App';
import { name as appName } from './app.json';

registerBackgroundHandler();

AppRegistry.registerComponent(appName, () => App);
