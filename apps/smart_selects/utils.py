# -*- coding: utf-8 -*-

def unicode_sorter(sorter_input):
    """ This function implements sort keys for the german language according to 
    DIN 5007."""
    
    # key1: compare words lowercase and replace umlauts according to DIN 5007
    key1 = sorter_input.lower()
    key1 = key1.replace(u"ä", u"a")
    key1 = key1.replace(u"ö", u"o")
    key1 = key1.replace(u"ü", u"u")
    key1 = key1.replace(u"ß", u"ss")
    
    # key2: sort the lowercase word before the uppercase word and sort
    # the word with umlaut after the word without umlaut
    # key2=sorter_input.swapcase()
    
    # in case two words are the same according to key1, sort the words
    # according to key2. 
    return key1
