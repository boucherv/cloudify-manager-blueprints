import os
import imp
import sys

import testtools
from mock import patch

from test_upgrade import _create_mock_context


validate = imp.load_source(
    'validate', os.path.join(
        os.path.dirname(__file__),
        '../../components/manager/scripts/validate.py'))


os_distro = ('distro', '1')


class TestValidations(testtools.TestCase):
    node_properties = {
        'ignore_bootstrap_validations': False,
        'es_heap_size': '2g',
        'manager_resources_package': 'http://non-existing-domain.com/package'
    }
    CTX = _create_mock_context(node_properties, node_id='node', service='test')
    node_properties.update({'ignore_bootstrap_validations': 'True'})
    IGNORE_VALIDATIONS_CTX = _create_mock_context(
        node_properties, node_id='_node', service='test')

    @patch('validate.ctx', CTX)
    @patch('validate._get_os_distro', return_value=('redhat', '7'))
    @patch('validate._get_host_total_memory', return_value=100000000)
    @patch('validate._get_available_host_disk_space', return_value=100)
    @patch('validate._validate_resources_package_url', return_value=None)
    def test_successful_validation(self, *_):
        validate.validate()

    @patch('validate.ctx', IGNORE_VALIDATIONS_CTX)
    @patch('validate._get_os_distro', return_value=os_distro)
    @patch('validate._get_host_total_memory', return_value=1)
    @patch('validate._get_available_host_disk_space', return_value=1)
    @patch('validate._validate_resources_package_url', return_value=None)
    def test_failed_yet_ignored_validation(self, *_):
        validate.validate()

    @patch('validate.ctx', CTX)
    @patch('validate._get_os_distro', return_value=os_distro)
    @patch('validate._get_host_total_memory', return_value=1)
    @patch('validate._get_available_host_disk_space', return_value=1)
    def test_failed_validation(self, *_):
        validate.ctx.abort_operation = lambda message: sys.exit(message)
        ex = self.assertRaises(SystemExit, validate.validate)
        self.assertIn(
            validate._error('Cloudify Manager requires'),
            str(ex))
        self.assertIn(
            validate._error('The provided host does not have enough memory'),
            str(ex))
        self.assertIn(
            validate._error('The provided host does not have enough disk'),
            str(ex))
        self.assertIn(
            validate._error('The heapsize provided for Elasticsearch'),
            str(ex))
        self.assertIn(
            validate._error(
                "The Manager's Resources Package "
                "http://non-existing-domain.com/package"),
            str(ex))

    def test_fail_validate_resources_package_url(self):
        test_url = 'http://non-existent-domain.com/non-existent-file.tar.gz'
        error = validate._validate_resources_package_url(test_url)
        desired_error = (validate._error(
            "The Manager's Resources Package {0} is not accessible "
            "(HTTP Error: {1})".format(test_url, '404')))
        self.assertEqual(desired_error, error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_os_distro', return_value=os_distro)
    def test_validate_supported_distros_ok(self, _):
        error = validate._validate_supported_distros(['distro'], ['1'])
        self.assertIsNone(error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_os_distro', return_value=os_distro)
    def _test_fail_validate_supported_distros(self, _, distros, versions):
        current_distro, current_version = validate._get_os_distro()
        error = validate._validate_supported_distros(distros, versions)
        desired_error = 'Manager requires either '
        self.assertIn(desired_error, error)

    def test_fail_validate_supported_distros_bad_distro(self):
        self._test_fail_validate_supported_distros(['bla'], ['1'])

    def test_fail_validate_supported_distros_bad_version(self):
        self._test_fail_validate_supported_distros(['distro'], ['2'])

    def test_fail_validate_supported_distros_bad_version_and_distro(self):
        self._test_fail_validate_supported_distros(['bla'], ['2'])

    @patch('validate.ctx', CTX)
    @patch('validate._get_host_total_memory', return_value=1023)
    def test_fail_validate_physical_memory(self, _):
        error = validate._validate_sufficient_memory(1024)
        desired_error = validate._error(
            'The provided host does not have enough memory')
        self.assertIn(desired_error, error)

    @patch('validate.ctx', CTX)
    def test_validate_physical_memory(self):
        error = validate._validate_sufficient_memory(1)
        self.assertIsNone(error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_available_host_disk_space', return_value=1)
    def test_fail_validate_available_disk_space(self, _):
        error = validate._validate_sufficient_disk_space(2)
        desired_error = validate._error(
            'The provided host does not have enough disk space')
        self.assertIn(desired_error, error)

    @patch('validate.ctx', CTX)
    def test_validate_available_disk_space(self):
        error = validate._validate_sufficient_disk_space(1)
        self.assertIsNone(error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_host_total_memory', return_value=100)
    def test_fail_validate_es_heap_size_large_gap(self, _):
        error = validate._validate_es_heap_size('90m', 11)
        desired_error = validate._error(
            'The heapsize provided for Elasticsearch')
        self.assertIn(desired_error, error)

    @patch('validate.ctx', CTX)
    @patch('validate._get_host_total_memory', return_value=100)
    def test_fail_validate_es_heap_size(self, _):
        error = validate._validate_es_heap_size('101m', 1)
        desired_error = validate._error(
            'The heapsize provided for Elasticsearch')
        self.assertIn(desired_error, error)

    @patch('validate.ctx', CTX)
    def test_validate_es_heap_size(self):
        error = validate._validate_es_heap_size('512m', 512)
        self.assertIsNone(error)