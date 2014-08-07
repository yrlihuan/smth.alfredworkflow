# -*- encoding=utf-8 -*-

import sys
import os
import json
import time
import urllib2
import xml.etree.ElementTree as ET

import alfred

def safe_get_text(elem):
  if elem is not None:
    return elem.text.strip()
  else:
    return ''

def safe_get_time(elem):
  if elem is not None:
    s = elem.text.strip()
    p = "%a, %d %b %Y %H:%M:%S %Z"
    try:
      t = time.mktime(time.strptime(s, p))
    except:
      return ''

    dt = time.time() - t
    if dt > 3600 * 24 * 2:
      return u'%.0f 天前' % (dt / 3600.0 / 24.0)
    elif dt > 3600 * 24:
      return u'昨天'
    elif dt > 3600:
      return u'%.0f小时前' % (dt / 3600.0)
    elif dt > 60:
      return u'%.0f分钟前' % (dt / 60.0)
    else:
      return u'%.0f秒前' % (dt, )

  else:
    return ''

def get_rss(url):
  try:
    s = urllib2.urlopen(url).read()
  except:
    return []

  s = s.decode('gb18030').encode('utf-8')
  s = s.replace('gb2312', 'utf-8')
  tree = ET.fromstring(s)
  items = tree.findall('./channel/item')

  result = []
  for item in items:
    title = safe_get_text(item.find('./title'))
    link = safe_get_text(item.find('./link'))
    desc = safe_get_text(item.find('./description'))
    since = safe_get_time(item.find('./pubDate'))

    result.append({'title': title, 'link': link, 'desc': desc, 'since': since})

  return result

def get_board(board_id):
  return get_rss('http://www.newsmth.net/nForum/rss/board-%s' % board_id)

def get_top10():
  return get_rss('http://www.newsmth.net/nForum/rss/topten')

def load_boards():
  cache_file = 'boards.json'
  if os.path.exists(cache_file):
    return json.load(open(cache_file))

  s = open('boards.html').read()
  tree = ET.fromstring(s)
  items = tree.findall('.//a')

  boards = []
  import pinyin
  conv = pinyin.Converter()
  for item in items:
    title = item.get('title')
    href = item.get('href')
    if not title or not href:
      continue

    board_id = href.split('/')[-1]
    boards.append({
      'title': title,
      'href': href,
      'id': board_id,
      'pinyin': conv.convert(title),
    })

  # save cache
  fout = open(cache_file, 'w')
  json.dump(boards, fout)
  fout.close()

  return boards

def display_top10():
  fb = alfred.Feedback()

  items = get_top10()
  for item in items:
    fb.addItem(title=item['title'], subtitle=item['since'], arg=item['link'])

  fb.output()

def display_matched_boards(q):
  boards = load_boards()
  q = q.lower()

  matches = []
  for info in boards:
    pinyin = info['pinyin'].strip().lower().replace(' ', '').replace(u'·', '').replace(u':', '')
    if q in pinyin:
      p = pinyin.index(q)
      matches.append([info, p])

  fb = alfred.Feedback()
  if not matches:
    fb.addItem(title=u"没有匹配的板块", valid=False)
  else:
    matches.sort(key=lambda t: (t[1], t[0]['pinyin']))
    for info, p in matches:
      fb.addItem(title=info['title'],
                 arg=info['id'],
                 autocomplete="> %s" % info['id'],
                 valid=False)

  fb.output()

def display_board(board_id):
  fb = alfred.Feedback()

  boards = load_boards()
  valid_id = False
  for info in boards:
    if board_id == info['id']:
      valid_id = True
      break

  if valid_id:
    items = get_board(board_id)
    for item in items:
      fb.addItem(title=item['title'], subtitle=item['since'], arg=item['link'])
  else:
    fb.addItem(title=u'无法找到对应的版面', valid=False)

  fb.output()

def run(query):
  q = query.strip()
  if q == '':
    display_top10()
  elif '>' in q:
    board_id = q.split('>')[-1].strip()
    display_board(board_id)
  else:
    display_matched_boards(q)

if __name__ == '__main__':
  if len(sys.argv) == 1:
    q = ''
  else:
    q = sys.argv[1]

  run(q)
