import pandas as pd
import wget
import shutil
import os
from zipfile import ZipFile
from fuzzywuzzy import fuzz
import csv
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer


# calculate_data_stats(book_filename,summary_filename)
#
# calculates number of sentences, number of words, file size
# for books and summaries
def calculate_data_stats(book_filename, summary_filename):
    parser = PlaintextParser.from_file(book_filename, Tokenizer("english"))
    num_sentences_in_book = len(parser.document.sentences)
    num_words_in_book = len(parser.document.words)
    file_info = os.stat(book_filename)
    file_size_book = file_info.st_size
    parser = PlaintextParser.from_file(summary_filename, Tokenizer("english"))
    num_sentences_in_summary = len(parser.document.sentences)
    num_words_in_summary = len(parser.document.words)
    file_info = os.stat(summary_filename)
    file_size_summary = file_info.st_size
    return [num_sentences_in_book, num_words_in_book, file_size_book,
            num_sentences_in_summary, num_words_in_summary, file_size_summary]


# data_list()
#
# load book summaries
# load metadata about Project Gutenberg books
# match summaries and books on title
# return list of matched books and summaries
# also saves this list to file
# also return list of titles and summaries
def data_list():
    # otherwise the summaries are cropped
    pd.set_option("display.max_colwidth", 100000)
    df = pd.read_csv("../data/booksummaries.txt", sep='\t', header=None)
    pg_df = pd.read_csv("../data/SPGC-metadata-2018-07-18.csv")
    # match summaries and books on title
    # requires exact title, does not check author
    # multiple books may be assigned to a summary
    df_combined = df.merge(pg_df, left_on=2, right_on='title')
    # save a list of the titles and authors
    df_titles = df_combined[['title', 'author', 3, 'id']]
    df_titles.to_csv('matched_titles.csv')
    df_summaries = df[[2, 6]]
    return df_titles, df_summaries


# calculate_author_match(author1,author2)
#
# calculates the match between author names
# returns a value between 0 and 100
# 0 indicates no match, 100 indicates perfect match
# with different orders of names and extra information about 40 is a good threshold
# assumption made that if no author is provided there is a match
def calculate_author_match(author1, author2):
    if isinstance(author1, str) and isinstance(author2, str):
        return fuzz.partial_ratio(author1, author2)
    else:
        return 100


# download_from_gutenberg(pg_id)
#
# downloads the book zip file from Project Gutenberg into the current directory
# some of the links do not work
# for PGabcde, the address is http://aleph.gutenberg.org/a/b/c/d/abcde/abcde.zip
def download_from_gutenberg(pg_id):
    web_page = "http://aleph.gutenberg.org/"
    for d in str(pg_id)[:-1]:
        web_page = web_page + str(d) + "/"
    web_page = web_page + str(pg_id) + "/" + str(pg_id) + ".zip"
    file_exists = True
    try:
        wget.download(web_page)
    except:
        print("404 error")
        file_exists = False
    return file_exists


# extract_book(pg_index)
#
# unzip the book and move to books folder
# remove zip file afterwards
def extract_book(pg_index, zip_filename, text_filename, book_filename):
    with ZipFile(zip_filename, 'r') as zipObj:
        zipObj.extractall()
    if os.path.exists(text_filename):
        shutil.move(text_filename, book_filename)
    else:
        # some files have an extra folder before the file
        shutil.move(str(pg_index) + '/' + text_filename, book_filename)
        shutil.rmtree(str(pg_index))
    os.remove(zip_filename)


# save_summary(df_summaries, new_title, summary_filename)
#
# saves the summary to the summary folder
def save_summary(df_summaries, new_title, summary_filename):
    new_summary = df_summaries[df_summaries[2] == new_title][6].to_string()[6:]
    with open(summary_filename, 'w') as f:
        f.write(new_summary)


# save_clean_book(book_filename,clean_book_filename)
#
# removes information about project gutenberg from the book
# replaces the book file with the cleaned book
def save_clean_book(book_filename, clean_book_filename):
    book = open(book_filename, 'r', encoding='latin-1')
    clean_book = open(clean_book_filename, 'w')
    write_lines = False
    # TODO: some of the older books do not match this formatting
    # and end up with no lines of text output
    for l in book:
        if (l[:12] == '*** START OF') or (l[:11] == '***START OF') or (l[:11] == '*END*THE SM'):
            write_lines = True
        elif (l[:10] == '*** END OF') or (l[:9] == '***END OF'):
            write_lines = False
        elif write_lines:
            clean_book.write(l)
    book.close()
    clean_book.close()
    # if the formatting didn't match the above, just use the complete
    # book with project gutenberg information
    if os.stat(clean_book_filename).st_size == 0:
        book = open(book_filename, 'r', encoding='latin-1')
        clean_book = open(clean_book_filename, 'w')
        for l in book:
            clean_book.write(l)
        book.close()
        clean_book.close()
    os.remove(book_filename)
    os.rename(clean_book_filename, book_filename)


# load info about books and summaries
df_titles, df_summaries = data_list()
# for each item, check if title is already in database
# if it isn't, check if it can be downloaded
# move to books folder
# process book to remove metadata and license information
shutil.rmtree('../data/books')
shutil.rmtree('../data/summaries')
os.makedirs('../data/books')
os.makedirs('../data/summaries')
titles = dict()
stats = []
for index, row in df_titles.iterrows():
    new_title = row['title']
    pg_index = row['id'][2:]
    pg_author = row['author']
    summaries_author = row[3]
    if ((new_title not in titles) and (calculate_author_match(pg_author, summaries_author) > 40)):
        file_exists = download_from_gutenberg(pg_index)
        if (file_exists):
            zip_filename = str(pg_index) + ".zip"
            text_filename = str(pg_index) + ".txt"
            book_filename = '../data/books/' + text_filename
            clean_book_filename = '../data/books/clean-' + text_filename
            summary_filename = '../data/summaries/' + text_filename
            extract_book(pg_index, zip_filename, text_filename, book_filename)
            save_summary(df_summaries, new_title, summary_filename)
            save_clean_book(book_filename, clean_book_filename)
            titles[new_title] = pg_index
            print(new_title)
            b_s_stats = calculate_data_stats(book_filename, summary_filename)
            new_stats = [new_title, pg_index, pg_author, summaries_author]
            new_stats.extend(b_s_stats)
            stats.append(new_stats)
with open('data_stats.csv', 'w') as csvFile:
    writer = csv.writer(csvFile)
    writer.writerows(stats)
csvFile.close()
