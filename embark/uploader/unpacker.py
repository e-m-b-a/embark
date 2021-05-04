import gzip
import logging
import os
import re
import shutil


class unpacker:
    """
       Class unpacker
       This class use shutil function to unpack files
    """

    def __init__(self):
        # default formats: zip, tar, gztar, bztar, xztar

        # register additional formats ( gz )
        shutil.register_unpack_format('gz', ['.gz', ], self.gunzip_file)
        pass

    @staticmethod
    def gunzip_file(file_name, work_dir):
        """
            special unzip function for .gz files

            :param file_name: file name of the gz file
            :param work_dir: directory where the archive is located

            :return:
        """

        # see warning about filename
        filename = os.path.split(file_name)[-1]
        filename = re.sub(r"\.gz$", "", filename, flags=re.IGNORECASE)

        # extract .gz file
        with gzip.open(file_name, 'rb') as f_in:
            with open(os.path.join(work_dir, filename), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    # TODO: maybe make unique
    @staticmethod
    def unpack(file_location, extract_dir=None):
        """
            unpack function

            :param file_location: file location of the archive
            :param extract_dir: output directory where the archive contents are saved

            :return: Boolean determining status
        """

        try:
            if extract_dir:
                shutil.unpack_archive(file_location, extract_dir)
            else:
                shutil.unpack_archive(file_location)
            logging.debug("Unpacked file successful: %s", file_location)
            return True
        except shutil.ReadError:
            logging.error("Format .%s is not supported", file_location.split(".", 1)[1])
            raise ValueError
        except Exception as ex:
            logging.error("Undefined Error during unpacking file: %s", file_location)
            logging.error(ex)
            raise ex

    @staticmethod
    def get_supported_formats():
        """
            returning supported formats

            :return: list of all supported formats for unpacking
        """

        return [name for (name, extensions, description) in shutil.get_unpack_formats()]
