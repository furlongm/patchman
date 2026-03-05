# Copyright 2025 Marcus Furlong <furlongm@gmail.com>
#
# This file is part of Patchman.
#
# Patchman is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Patchman is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchman. If not, see <http://www.gnu.org/licenses/>

from django.test import TestCase, override_settings

from packages.models import Package
from reports.utils import (
    _get_package_type, _get_repo_type, parse_packages, parse_repos,
)
from repos.models import Repository


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ParsePackagesTests(TestCase):
    """Tests for parse_packages() function - Protocol 1 text parsing."""

    def test_parse_packages_single_package(self):
        """Test parsing a single package string."""
        pkg_str = "'nginx' '' '1.18.0' '6ubuntu14' 'amd64' 'deb'"
        packages = parse_packages(pkg_str)
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0][0], 'nginx')

    def test_parse_packages_multiple_packages(self):
        """Test parsing multiple package strings."""
        pkg_str = """'nginx' '' '1.18.0' '6ubuntu14' 'amd64' 'deb'
'curl' '' '7.81.0' '1' 'amd64' 'deb'
'vim' '' '8.2.0' '1' 'amd64' 'deb'"""
        packages = parse_packages(pkg_str)
        self.assertEqual(len(packages), 3)
        self.assertEqual(packages[0][0], 'nginx')
        self.assertEqual(packages[1][0], 'curl')
        self.assertEqual(packages[2][0], 'vim')

    def test_parse_packages_with_epoch(self):
        """Test parsing package with epoch."""
        pkg_str = "'vim' '2' '8.2.0' '1' 'amd64' 'deb'"
        packages = parse_packages(pkg_str)
        self.assertEqual(packages[0][1], '2')

    def test_parse_packages_rpm_format(self):
        """Test parsing RPM package format."""
        pkg_str = "'httpd' '0' '2.4.57' '5.el9' 'x86_64' 'rpm'"
        packages = parse_packages(pkg_str)
        self.assertEqual(packages[0][0], 'httpd')
        self.assertEqual(packages[0][5], 'rpm')

    def test_parse_packages_empty_string(self):
        """Test parsing empty string returns empty list."""
        packages = parse_packages('')
        # Empty string results in empty list
        self.assertEqual(len(packages), 0)

    def test_parse_packages_strips_quotes(self):
        """Test that quotes are removed from parsed values."""
        pkg_str = "'nginx' '' '1.18.0' '6ubuntu14' 'amd64' 'deb'"
        packages = parse_packages(pkg_str)
        # Quotes should be stripped
        self.assertNotIn("'", packages[0][0])


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class ParseReposTests(TestCase):
    """Tests for parse_repos() function - Protocol 1 text parsing."""

    def test_parse_repos_single_repo(self):
        """Test parsing a single repo string."""
        repo_str = "'deb' 'Ubuntu Main' 'ubuntu-main' '500' 'http://archive.ubuntu.com/ubuntu'"
        repos = parse_repos(repo_str)
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0][0], 'deb')

    def test_parse_repos_multiple_repos(self):
        """Test parsing multiple repo strings."""
        repo_str = """'deb' 'Ubuntu Main' 'ubuntu-main' '500' 'http://archive.ubuntu.com/ubuntu'
'deb' 'Ubuntu Security' 'ubuntu-security' '500' 'http://security.ubuntu.com/ubuntu'"""
        repos = parse_repos(repo_str)
        self.assertEqual(len(repos), 2)

    def test_parse_repos_rpm_format(self):
        """Test parsing RPM repo format."""
        repo_str = "'rpm' 'Rocky BaseOS' 'baseos' '99' 'http://mirror.rockylinux.org/rocky/9/BaseOS/x86_64/os'"
        repos = parse_repos(repo_str)
        self.assertEqual(repos[0][0], 'rpm')
        self.assertEqual(repos[0][1], 'Rocky BaseOS')

    def test_parse_repos_empty_string(self):
        """Test parsing empty string returns empty list."""
        repos = parse_repos('')
        self.assertEqual(len(repos), 0)

    def test_parse_repos_strips_quotes(self):
        """Test that quotes are removed from parsed values."""
        repo_str = "'deb' 'Ubuntu Main' 'ubuntu-main' '500' 'http://archive.ubuntu.com/ubuntu'"
        repos = parse_repos(repo_str)
        self.assertNotIn("'", repos[0][0])
        self.assertNotIn("'", repos[0][1])


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class GetPackageTypeTests(TestCase):
    """Tests for _get_package_type() function."""

    def test_get_package_type_deb(self):
        """Test DEB package type detection."""
        self.assertEqual(_get_package_type('deb'), Package.DEB)
        self.assertEqual(_get_package_type('DEB'), Package.DEB)
        self.assertEqual(_get_package_type('Deb'), Package.DEB)

    def test_get_package_type_rpm(self):
        """Test RPM package type detection."""
        self.assertEqual(_get_package_type('rpm'), Package.RPM)
        self.assertEqual(_get_package_type('RPM'), Package.RPM)

    def test_get_package_type_arch(self):
        """Test Arch package type detection."""
        self.assertEqual(_get_package_type('arch'), Package.ARCH)

    def test_get_package_type_gentoo(self):
        """Test Gentoo package type detection."""
        self.assertEqual(_get_package_type('gentoo'), Package.GENTOO)

    def test_get_package_type_unknown(self):
        """Test unknown package type returns UNKNOWN."""
        self.assertEqual(_get_package_type(''), Package.UNKNOWN)
        self.assertEqual(_get_package_type('invalid'), Package.UNKNOWN)
        self.assertEqual(_get_package_type(None), Package.UNKNOWN)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
)
class GetRepoTypeTests(TestCase):
    """Tests for _get_repo_type() function."""

    def test_get_repo_type_deb(self):
        """Test DEB repo type detection."""
        self.assertEqual(_get_repo_type('deb'), Repository.DEB)
        self.assertEqual(_get_repo_type('DEB'), Repository.DEB)

    def test_get_repo_type_rpm(self):
        """Test RPM repo type detection."""
        self.assertEqual(_get_repo_type('rpm'), Repository.RPM)
        self.assertEqual(_get_repo_type('RPM'), Repository.RPM)

    def test_get_repo_type_arch(self):
        """Test Arch repo type detection."""
        self.assertEqual(_get_repo_type('arch'), Repository.ARCH)

    def test_get_repo_type_gentoo(self):
        """Test Gentoo repo type detection."""
        self.assertEqual(_get_repo_type('gentoo'), Repository.GENTOO)

    def test_get_repo_type_unknown(self):
        """Test unknown repo type returns None."""
        self.assertIsNone(_get_repo_type(''))
        self.assertIsNone(_get_repo_type('invalid'))
