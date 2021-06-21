import os
import shutil

from django.test import TestCase

from .archiver import Archiver
import unittest as ut


class unpacker_test(TestCase):

    def setUp(self):
        self.archiver = Archiver

    def test_supported_formats_extensions(self):
        expected_formats = ["zip", "tar", "gztar"]
        expected_extensions = [".zip", ".tar", ".tar.gz"]

        supported_formats = self.archiver.get_supported_formats()
        supported_extensions = self.archiver.get_supported_extensions()

        for arch_format in expected_formats:
            assert supported_formats.__contains__(arch_format)

        for extension in expected_extensions:
            assert supported_extensions.__contains__(extension)

    def test_format_check(self):
        self.assertTrue(self.archiver.check_extensions("testfile.zip"))
        self.assertFalse(self.archiver.check_extensions("testfile.bin"))

    def test_false_file(self):

        archive_name = "invalid.txt"

        # create invalid archive
        f = open(archive_name, "a")
        f.close()

        # check for error
        with self.assertRaises(ValueError):
            self.archiver.unpack(f.name)

        # delete file
        os.remove(archive_name)

    def test_archive_file(self):

        folder_name = "./archive"
        log_names = ["log"+str(i)+".bin" for i in range(10)]

        # create archive
        os.mkdir(folder_name)
        for log_name in log_names:
            log_file = open(folder_name + "/" + log_name, "a")
            log_file.close()

        self.archiver.pack(folder_name, 'zip', folder_name, '.')

        for log_name in log_names:
            os.remove(folder_name + "/" + log_name)
        os.rmdir(folder_name)

        # unzip archive and assert existance of file
        self.assertTrue(self.archiver.unpack("./archive.zip"))
        for log_name in log_names:
            self.assertTrue(os.path.isfile(log_name))

        # cleanup
        os.remove("./archive.zip")
        for log_name in log_names:
            os.remove(log_name)
