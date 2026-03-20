const fs = require('fs');
const path = require('path');

const targets = [
  path.join(__dirname, '..', 'node_modules', 'react-native', 'gradle', 'libs.versions.toml'),
  path.join(__dirname, '..', 'node_modules', '@react-native', 'gradle-plugin', 'gradle', 'libs.versions.toml'),
  path.join(__dirname, '..', 'node_modules', 'expo-modules-core', 'android', 'ExpoModulesCorePlugin.gradle'),
];

for (const file of targets) {
  if (!fs.existsSync(file)) {
    console.log('[fix-kotlin-version] missing:', file);
    continue;
  }
  let text = fs.readFileSync(file, 'utf8');
  const before = text;
  text = text.replace(/kotlin = "1\.9\.24"/g, 'kotlin = "1.9.25"');
  text = text.replace(/: "1\.9\.24"/g, ': "1.9.25"');
  if (text !== before) {
    fs.writeFileSync(file, text, 'utf8');
    console.log('[fix-kotlin-version] patched', file);
  } else {
    console.log('[fix-kotlin-version] no change needed', file);
  }
}
