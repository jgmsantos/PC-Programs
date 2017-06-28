# coding=utf-8

import os
import urllib
from mimetypes import MimeTypes

from ..utils import utils
from ..utils import xml_utils
from ..data import attributes


messages = []
mime = MimeTypes()


class SPSXMLContent(xml_utils.XMLContent):

    def __init__(self, content):
        xml_utils.XMLContent.__init__(self, content)

    @property
    def xml(self):
        _xml, e = xml_utils.load_xml(self.content)
        if _xml is not None:
            return _xml

    def normalize(self):
        xml_utils.XMLContent.normalize(self)
        self.insert_mml_namespace()
        if self.xml is not None:
            if 'contrib-id-type="' in self.content:
                for contrib_id, url in attributes.CONTRIB_ID_URLS.items():
                    self.content = self.content.replace(' contrib-id-type="' + contrib_id + '">' + url, ' contrib-id-type="' + contrib_id + '">')
            #content = remove_xmllang_off_article_title(content)
            self.content = self.content.replace('<comment content-type="cited"', '<comment')
            self.content = self.content.replace(' - </title>', '</title>').replace('<title> ', '<title>')
            self.content = self.content.replace('&amp;amp;', '&amp;')
            self.content = self.content.replace('&amp;#', '&#')
            self.content = self.content.replace('dtd-version="3.0"', 'dtd-version="1.0"')
            self.content = self.content.replace('publication-type="conf-proc"', 'publication-type="confproc"')
            self.content = self.content.replace('publication-type="legaldoc"', 'publication-type="legal-doc"')
            self.content = self.content.replace('publication-type="web"', 'publication-type="webpage"')
            self.content = self.content.replace(' rid=" ', ' rid="')
            self.content = self.content.replace(' id=" ', ' id="')
            self.content = xml_utils.pretty_print(self.content)
            self.remove_xmllang_from_element('article-title')
            self.remove_xmllang_from_element('source')
            self.content = self.content.replace('> :', '>: ')
            self.normalize_references()
            for tag in ['article-title', 'trans-title', 'kwd', 'source']:
                self.remove_styles_from_tagged_content(tag)
            self.content = self.content.replace('<institution content-type="normalized"/>', '')
            self.content = self.content.replace('<institution content-type="normalized"></institution>', '')

    def insert_mml_namespace(self):
        if '</math>' in self.content:
            new = []
            for part in self.content.replace('</math>', '</math>BREAK-MATH').split('BREAK-MATH'):
                before = part[:part.find('<math')]
                math = part[part.find('<math'):]
                part = before + math.replace('<', '<mml:').replace('<mml:/', '</mml:')
                new.append(part)
            self.content = ''.join(new)

    def remove_xmllang_from_element(self, element_name):
        start = '<' + element_name + ' '
        mark = '<' + element_name + '~BREAK~'
        end = '</' + element_name + '>'
        if start in self.content:
            new = []
            for item in self.content.replace(start, mark).split('~BREAK~'):
                if item.strip().startswith('xml:lang') and end in item:
                    item = item[item.find('>'):]
                new.append(item)
            self.content = ''.join(new)

    def remove_styles_from_tagged_content(self, tag):
        open_tag = '<' + tag + '>'
        close_tag = '</' + tag + '>'
        self.content = self.content.replace(open_tag + ' ', ' ' + open_tag).replace(' ' + close_tag, close_tag + ' ')
        self.content = self.content.replace(open_tag, '~BREAK~' + open_tag).replace(close_tag, close_tag + '~BREAK~')
        parts = []
        for part in self.content.split('~BREAK~'):
            if part.startswith(open_tag) and part.endswith(close_tag):
                data = part[len(open_tag):]
                data = data[0:-len(close_tag)]
                data = ' '.join([w.strip() for w in data.split()])
                part = open_tag + data + close_tag
                remove_all = False
                if tag == 'source' and len(parts) > 0:
                    remove_all = 'publication-type="journal"' in parts[len(parts)-1]
                for style in ['italic', 'bold', 'italic']:
                    if remove_all or part.startswith(open_tag + '<' + style + '>') and part.endswith('</' + style + '>' + close_tag):
                        part = part.replace('<' + style + '>', '').replace('</' + style + '>', '')
            parts.append(part)
        self.content = ''.join(parts).replace(open_tag + ' ', ' ' + open_tag).replace(' ' + close_tag, close_tag + ' ')

    def normalize_references(self):
        self.content = self.content.replace('<ref', '~BREAK~<ref')
        self.content = self.content.replace('</ref>', '</ref>~BREAK~')
        refs = []
        for item in [SPSRefXMLContent(item) for item in self.content.split('~BREAK~')]:
            item.normalize()
            refs.append(item.content)
        self.content = ''.join(refs)

    def normalize_href_values(self):
        for href in self.doc.hrefs:
            if href.is_internal_file:
                new = self.workarea.name_with_extension(href.src, href.src)
                self.replacements_href_values.append((href.src, new))
                if href.src != new:
                    self.content = self.content.replace('href="' + href.src + '"', 'href="' + new + '"')


class SPSRefXMLContent(xml_utils.XMLContent):

    def __init__(self, content):
        xml_utils.XMLContent.__init__(self, content)

    def normalize(self):
        if self.content.startswith('<ref') and self.content.endswith('</ref>'):
            self.fix_mixed_citation_label()
            self.fix_book_data()
            self.fix_mixed_citation_ext_link()
            self.fix_source()

    def fix_book_data(self):
        if 'publication-type="book"' in self.content and '</article-title>' in self.content:
            self.content = self.content.replace('article-title', 'chapter-title')
        if 'publication-type="book"' in self.content and not '</source>' in self.content:
            self.content = self.content.replace('chapter-title', 'source')

    def fix_mixed_citation_ext_link(self):
        replacements = {}
        if '<ext-link' in self.content and '<mixed-citation>' in self.content:
            mixed_citation = self.content[self.content.find('<mixed-citation>'):]
            mixed_citation = mixed_citation[:mixed_citation.find('</mixed-citation>')+len('</mixed-citation>')]
            new_mixed_citation = mixed_citation
            if not '<ext-link' in mixed_citation:
                for ext_link_item in self.content.replace('<ext-link', '~BREAK~<ext-link').split('~BREAK~'):
                    if ext_link_item.startswith('<ext-link'):
                        if '</ext-link>' in ext_link_item:
                            ext_link_element = ext_link_item[0:ext_link_item.find('</ext-link>')+len('</ext-link>')]
                            ext_link_content = ext_link_element[ext_link_element.find('>')+1:]
                            ext_link_content = ext_link_content[0:ext_link_content.find('</ext-link>')]
                            if '://' in ext_link_content:
                                urls = ext_link_content.split('://')
                                if not ' ' in urls[0]:
                                    replacements[ext_link_content] = ext_link_element
                for ext_link_content, ext_link_element in replacements.items():
                    new_mixed_citation = new_mixed_citation.replace(ext_link_content, ext_link_element)
                if new_mixed_citation != mixed_citation:
                    self.content = self.content.replace(mixed_citation, new_mixed_citation)

    def fix_mixed_citation_label(self):
        if '<label>' in self.content and '<mixed-citation>' in self.content:
            mixed_citation = self.content[self.content.find('<mixed-citation>')+len('<mixed-citation>'):self.content.find('</mixed-citation>')]
            label = self.content[self.content.find('<label>')+len('<label>'):self.content.find('</label>')]
            changed = mixed_citation
            if not '<label>' in mixed_citation:
                if not changed.startswith(label):
                    sep = ' '
                    if changed.startswith('.'):
                        changed = changed[1:].strip()
                        sep = '. '
                    if label.endswith('.'):
                        label = label[0:-1]
                        sep = '. '
                    changed = label + sep + changed
                if mixed_citation != changed:
                    if mixed_citation in self.content:
                        self.content = self.content.replace('<mixed-citation>' + mixed_citation + '</mixed-citation>', '<mixed-citation>' + changed + '</mixed-citation>')
                    else:
                        print('Unable to insert label to mixed_citation')
                        print('mixed-citation:')
                        print(mixed_citation)
                        print('self.content:')
                        print(self.content)
                        print('changes:')
                        print(changed)

    def fix_source(self):
        if '<source' in self.content and '<mixed-citation' in self.content:
            source = self.content[self.content.find('<source'):]
            if '</source>' in source:
                source = source[0:source.find('</source>')]
                source = source[source.find('>')+1:]
                mixed_citation = self.content[self.content.find('<mixed-citation'):]
                if '</mixed-citation>' in mixed_citation:
                    mixed_citation = mixed_citation[0:mixed_citation.find('</mixed-citation>')]
                    mixed_citation = mixed_citation[mixed_citation.find('>')+1:]
                    s = source.replace(':', ': ')
                    if not source in mixed_citation and s in mixed_citation:
                        self.content = self.content.replace(source, s)

    def replace_mimetypes(self):
        r = self.content
        if 'mimetype="replace' in self.content:
            self.content = self.content.replace('mimetype="replace', '_~BREAK~MIME_MIME:')
            self.content = self.content.replace('mime-subtype="replace"', '_~BREAK~MIME_')
            r = ''
            for item in self.content.split('_~BREAK~MIME_'):
                if item.startswith('MIME:'):
                    f = item[5:]
                    f = f[0:f.rfind('"')]
                    result = ''
                    if os.path.isfile(self.src_path + '/' + f):
                        result = mime.guess_type(self.src_path + '/' + f)
                    else:
                        url = urllib.pathname2url(f)
                        result = mime.guess_type(url)
                    try:
                        result = result[0]
                        if '/' in result:
                            m, ms = result.split('/')
                            r += 'mimetype="' + m + '" mime-subtype="' + ms + '"'
                        else:
                            pass
                    except:
                        pass
                else:
                    r += item
        else:
            utils.debugging('.............')
        self.content = r
