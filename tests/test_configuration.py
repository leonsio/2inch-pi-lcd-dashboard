"""Configuration checks run without Raspberry Pi hardware or external services."""
import copy
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import yaml

from dashboard_config import ConfigError, ROOT, load_config
from dashboard_navigation import DashboardNavigator


class ConfigurationTests(unittest.TestCase):
    def load_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.yaml'
            path.write_text(text)
            return load_config(path)

    def test_default_template(self):
        cfg = load_config(ROOT / 'config.example.yaml')
        self.assertEqual(cfg.LCD_DEVICE, '2inch')
        self.assertEqual(len(cfg.PAGES), 6)
        self.assertTrue(Path(cfg.FONT_PATH).is_file())

    def test_overrides_replace_pages_and_preserve_types(self):
        cfg = self.load_text('system: {}\nBUTTONS_ENABLED: false\npre_shutdown: null\nPAGES:\n  - name: only\n    layout: {row1cell1: cpu}\n')
        self.assertIs(cfg.BUTTONS_ENABLED, False)
        self.assertIsNone(cfg.pre_shutdown)
        self.assertEqual(cfg.GRID_COLS, 3)
        self.assertEqual(self.load_text('FAST_INTERVAL: 0.5').FAST_INTERVAL, 0.5)
        self.assertEqual([p['name'] for p in cfg.PAGES], ['only'])

    def test_invalid_settings(self):
        for text in ('', '[]', 'BUTTONS_ENABLED: "false"', 'GRID_ROWS: 0',
                     'GRID_ROWS: true', 'DISPLAY_BACKLIGHT: 101',
                     'LCD_DEVICE: other', 'SHOW_PER_CROE: true',
                     'SHOW_PER_CORE: false\nSHOW_PER_CORE: true',
                     'REQUEST_TIMEOUT: .nan', 'C_GRID: null',
                     'pre_shutdown: true', 'PAGES: []',
                     'BUTTONS_ENABLED: true\nGPIO_BUTTON_OK: 19'):
            with self.subTest(text=text), self.assertRaises(ConfigError):
                self.load_text(text)

    def test_python_object_tags_rejected_without_execution(self):
        with patch('os.system') as execute:
            with self.assertRaises(ConfigError):
                self.load_text('pre_shutdown: !!python/object/apply:os.system ["touch sentinel"]')
            execute.assert_not_called()

    def test_command_remains_data(self):
        with patch('subprocess.run') as execute:
            cfg = self.load_text('pre_shutdown: [systemctl, stop, example.service]')
            self.assertEqual(cfg.pre_shutdown, ['systemctl', 'stop', 'example.service'])
            execute.assert_not_called()

    def test_invalid_layouts(self):
        page = {'name': 'main', 'layout': {'row1cell1': 'cpu'}}
        variants = []
        for slot in ({'module': 'cpu', 'colspan': 4},
                     {'module': 'cpu', 'selectable': 'false'},
                     {'module': 'cpu', 'target_page': 'missing'}):
            p = copy.deepcopy(page)
            p['layout']['row1cell1'] = slot
            variants.append([p])
        variants += [[page, page], [{'name': 'detail', 'navigation': 'detail', 'layout': {}}],
                     [{'name': 'main', 'layout': {'row1cell1': {'module': 'cpu', 'colspan': 2}, 'row1cell2': 'ram'}}]]
        for pages in variants:
            with self.subTest(pages=pages), self.assertRaises(ConfigError):
                self.load_text(yaml.safe_dump({'system': {}, 'PAGES': pages}))

    def test_docs_examples_and_navigation(self):
        document = (ROOT / 'docs/Configuration.md').read_text()
        examples = re.findall(r'```yaml\n(.*?)```', document, re.S)
        self.assertEqual(len(examples), 14)
        for example in examples:
            with self.subTest(example=example):
                self.load_text(example)
        cfg = self.load_text(examples[3])
        nav = DashboardNavigator(cfg.PAGES)
        self.assertTrue(nav.open_selected())
        self.assertEqual(nav.current_page['name'], 'system_detail')
        self.assertTrue(nav.back())
        self.assertEqual(nav.selected_key, 'row1cell1')
        nav.move_next()
        self.assertEqual(nav.selected_key, 'row1cell3')

    def test_readme_example(self):
        text = (ROOT / 'README.md').read_text()
        for example in re.findall(r'```yaml\n(.*?)```', text, re.S):
            self.load_text(example)

    def test_errors_do_not_echo_secrets(self):
        with self.assertRaises(ConfigError) as caught:
            self.load_text('HOME_ASSISTANT_TOKEN: [SECRET: broken')
        self.assertNotIn('SECRET', str(caught.exception))

    def test_missing_file(self):
        with self.assertRaisesRegex(ConfigError, 'Copy config.example.yaml'):
            load_config(ROOT / 'does-not-exist.yaml')


if __name__ == '__main__':
    unittest.main()
