import csv
import logging

logger = logging.getLogger(__name__)


def _get_text(value):
    if len(value) > 1 and value[0] == '"':
        value = value[1:-1]
        return value
    elif value in ["NULL", "None"]:
        return None
    else:
        return value


def csv_map(reader, key_column=0):
    first_row = []
    n = 0

    try:
        for row in reader:
            if not row:
                print("Warning: empty row")
                continue
            try:
                n += 1
                if n == 1:
                    first_row = row
                    continue

                newrow = {}
                for j, k in enumerate(row):
                    newrow[_get_text(first_row[j])] = _get_text(k)

                yield _get_text(row[key_column]), newrow
            except Exception as e:
                msg = "Error while reading row: %s " % row
                print(msg)
                logger.exception(msg)
    except csv.Error as e:
        msg = 'line %d: %s' % (reader.line_num, e)
        print(msg)
        logger.exception(msg)


def dict_from_csv(reader, key_column=0):
    dic = {}
    for key, row in csv_map(reader, key_column):
        dic[key] = row

    return dic


def list_from_csv(reader):
    row_list = []
    for key, row in csv_map(reader):  # @UnusedVariable
        row_list.append(row)
    return row_list
