# pylint: disable= C0201
import csv
import re

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEST_PATH = f"{BASE_DIR}/test-data"

TEST_CMD = f"cd /var/www/emba && sudo ./emba.sh -p ./scan-profiles/default-scan-no-notify.emba -f /var/www/active/a4ca8bb3-e95e-42bb-a812-67f5a7ee0987/DIR300B5_FW214WWB01.bin"

# class TestBoundedExecutor(TestCase):

#     def setUp(self):
#         pass

#     # TODO: add timeout
#     def test_non_blocking_overflow(self):
# 
#         fut_list = []

#         for _ in range(MAX_WORKERS + MAX_QUEUE):
#             # if testing under windows use "timeout /T 5" instead of "sleep 5"
#             fut = BoundedExecutor.submit(BoundedExecutor.run_emba_cmd, "sleep 5")
#             self.assertIsNotNone(fut)
#             fut_list.append(fut)

#         for _ in range(MAX_WORKERS):
#             fut = BoundedExecutor.submit(BoundedExecutor.run_emba_cmd, "sleep 5")
#             self.assertIsNone(fut)

#         for fut in fut_list:
#             fut.result()
def csv_read(path):
    res_dict = {}
    with open(path, newline='\n', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        csv_list = []
        for _row in csv_reader:
            # remove NA
            if "NA" in _row:
                _row.remove("NA")
            # remove empty
            if "" in _row:
                _row.remove("")
            csv_list.append(_row)
            for _element in csv_list:
                if _element[0] == "version_details":
                    res_dict[_element[1]] = _element[2:]
                elif len(_element) == 2:
                    res_dict[_element[0]] = _element[1]
                elif len(_element) == 3:
                    if not _element[0] in res_dict.keys():
                        res_dict[_element[0]] = {}
                    res_dict[_element[0]][_element[1]] = _element[2]
                else:
                    pass
    # debug print
    res_dict.pop('FW_path', None)

    entropy_value = res_dict.get("entropy_value", 0)
    # if type(entropy_value) is str:
    if isinstance(entropy_value, str):
        # entropy_value = re.findall(r'(\d+\.?\d*)', ' 7.55 bits per byte.')[0]
        entropy_value = re.findall(r'(\d+\.?\d*)', entropy_value)[0]
        entropy_value = entropy_value.strip('.')

    return res_dict


if __name__ == "__main__":
    print(csv_read(path=f"{TEST_PATH}/boundedexecutor/test.csv"))
