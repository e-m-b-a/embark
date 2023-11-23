from random import randrange
import os


def rnd_rgb_color():
    """
    Used for html colors ONLY
    """
    result = "rgb("
    for _value in range(2):                         # nosec
        result += str(randrange(255)) + ", "    # nosec
    return result + str(randrange(255)) + ")"   # nosec


def rnd_rgb_full():
    """
    Used for html colors ONLY
    """
    return "rgb(" + str(randrange(255)) + ", " + str(randrange(255)) + ", " + str(randrange(255)) + ", " + "0.2)"   # nosec


def get_size(start_path='.'):
    """
    returns directory size in bytes
    https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
    """
    total_size = 0
    for dirpath, _dirnames, filenames in os.walk(start_path):
        for file in filenames:
            file_path = os.path.join(dirpath, file)
            # skip if it is symbolic link
            if not os.path.islink(file_path):
                total_size += os.path.getsize(file_path)

    return total_size


def zip_check(content_list):
    """
    checks the contents against a pre defined list to ensure validity
    """
    check_list = [
        "emba_logs/html-report/emba.html",
        "emba_logs/html-report/index.html",
        "emba_logs/emba.log",
        "emba_logs/csv_logs/f50_base_aggregator.csv"]
    return all(value_ in content_list for value_ in check_list)


def cleanup_charfield(charfield) -> str:
    # clean-up for linux extensive os-descriptions
    if charfield.startswith("Linux"):
        charfield = charfield.split("/", 2)[:2]
        charfield = f"{charfield[0]}{charfield[1]}"
        charfield = (charfield[:16] + '..') if len(charfield) > 18 else charfield
    return charfield


if __name__ == '__main__':
    test_string = 'Linux / v2.6.33.2'
    print(cleanup_charfield(test_string))
