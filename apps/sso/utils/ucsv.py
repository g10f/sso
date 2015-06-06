# -*- coding: utf-8 -*-
import csv
import codecs
import cStringIO
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


def csv_map(reader, key_row=0):
    first_row = []
    n = 0
    
    try:
        for row in reader:
            if not row:
                print "Warning: empty row"
                continue
            try:
                n += 1
                if n == 1:
                    first_row = row
                    continue
                
                newrow = {}
                for j, k in enumerate(row): 
                    newrow[_get_text(first_row[j])] = _get_text(k)
                
                yield _get_text(row[key_row]), newrow 
            except Exception, e:
                msg = "Error while reading row: %s " % row
                print msg
                logger.exception(msg)
    except csv.Error, e:
        msg = 'line %d: %s' % (reader.line_num, e)
        print msg
        logger.exception(msg)
        
    
def dic_from_csv(reader, key_row=0):
    dic = {}
    for key, row in csv_map(reader, key_row):
        dic[key] = row
        
    return dic

def list_from_csv(reader):
    row_list = [] 
    for key, row in csv_map(reader):  # @UnusedVariable
        row_list.append(row)
    return row_list

def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        yield [unicode(cell, 'utf-8-sig') for cell in row]

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):  # @ReservedAssignment
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):  # @ReservedAssignment
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
