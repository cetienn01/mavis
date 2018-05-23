import unittest
from unittest import mock
import configparser
import tempfile
import shutil
import os

from mavis.schedule import pipeline as _pipeline
from mavis.main import main

from ...util import get_data

class TestReadBuildFile(unittest.TestCase):

    # TODO: test_skip_validate
    # TODO: test_no_skip
    # TODO: test_missing_summary
    # TODO: test_missing_pairing
    # TODO: test_missing_annotations
    # TODO: test_error_on_config_not_exists
    # TODO: test_loading_unsubmitted
    # TODO: test_loading_submitted
    # TODO: test_loading_completed
    # TODO: test_missing_validations
    # TODO: test_missing_dependency_job

    def setUp(self):
        self.exists_patcher = mock.patch('os.path.exists')
        self.exists_patcher.start().return_value = True

    def read_mock_config(self, content):
        with mock.patch('configparser.ConfigParser.read', configparser.ConfigParser.read_string):
            return _pipeline.Pipeline.read_build_file(content)

    def test_basic(self):
        content = """
[general]
outputdir = temp

[job1]
stage = validate
tasks = 1000
name = job1


[job2]
stage = annotate
name = job2
dependencies = job1

[job3]
stage = pairing
name = job3
dependencies = job2

[job4]
stage = summary
name = job4
dependencies = job3
        """
        result = self.read_mock_config(content)
        self.assertEqual('job3', result.pairing.name)
        self.assertEqual('job1', result.validations[0].name)
        self.assertEqual('job2', result.annotations[0].name)
        self.assertEqual(result.validations[0], result.annotations[0].dependencies[0])
        self.assertEqual(result.annotations[0], result.pairing.dependencies[0])
        self.assertEqual(result.pairing, result.summary.dependencies[0])

    def tearDown(self):
        self.exists_patcher.stop()


class TestBuildPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_output = tempfile.mkdtemp()
        # clear any environment variables
        self.env_patch = mock.patch('os.environ', {k:v for k, v in os.environ.items() if not k.startswith('MAVIS_')})
        self.env_patch.start()

    def test_basic(self):
        config = get_data('pipeline_config.cfg')

        with mock.patch('sys.argv', ['mavis', 'pipeline', '--output', self.temp_output, config]):
            self.assertEqual(0, main())
        build_file = os.path.join(self.temp_output, 'build.cfg')
        with open(build_file, 'r') as fh:
            print(fh.read())
        build = _pipeline.Pipeline.read_build_file(build_file)
        print(build)
        self.assertGreaterEqual(len(build.validations), 1)
        self.assertGreaterEqual(len(build.annotations), 1)
        self.assertIsNotNone(build.pairing)
        self.assertIsNotNone(build.summary)

    def test_basic_submit(self):
        pass

    # TODO: test pipeline failure
    # TODO: test conversion failure

    def tearDown(self):
        shutil.rmtree(self.temp_output)
        self.env_patch.stop()

