# -*- coding: utf-8 -*-
from re import compile, escape

from linguist.libs.scanner import Scanner

"""
Generic programming language tokenizer.

Tokens are designed for use in the language bayes classifier.
It strips any data strings or comments and preserves significant
language symbols.
"""

# Read up to 100KB
BYTE_LIMIT = 100000

# Start state on token, ignore anything till the next newline
SINGLE_LINE_COMMENTS = [
    r'//',  # C
    r'#',   # Python, Ruby
    r'%',   # Tex
]

# Start state on opening token, ignore anything until the closing
# token is reached.
MULTI_LINE_COMMENTS = [
    [r'/*', r'*/'],     # C
    [r'<!--', r'-->'],  # XML
    [r'{-', r'-}'],     # Haskell
    [r'(*', r'*)'],     # Coq
    [r'"""', r'"""'],   # Python
    [r"'''", r"'''"],   # Python
]

MULTI_LINE_COMMENT_DICT = dict([(s, escape(e))
                                for s, e in MULTI_LINE_COMMENTS])

START_SINGLE_LINE_COMMENT = '|'.join([r'\s*%s ' % escape(c) for c in SINGLE_LINE_COMMENTS])
START_MULTI_LINE_COMMENT = '|'.join([escape(c[0]) for c in MULTI_LINE_COMMENTS])


REGEX_SHEBANG = r'^#!.+'
REGEX_BOL = r'\n|\Z'
REGEX_DOUBLE_QUOTE = r'"'
REGEX_SINGLE_QUOTE = r"'"
REGEX_DOUBLE_END_QUOTE = r'[^\\]"'
REGEX_SINGLE_END_QUOTE = r"[^\\]'"
REGEX_NUMBER_LITERALS = r'(0x)?\d(\d|\.)*'
REGEX_SGML = r'<[^\s<>][^<>]*>'
REGEX_COMMON_PUNCTUATION = r';|\{|\}|\(|\)|\[|\]'
REGEX_REGULAR_TOKEN = r'[\w\.@#\/\*]+'
REGEX_COMMON_OPERATORS = r'<<?|\+|\-|\*|\/|%|&&?|\|\|?'
REGEX_EMIT_START_TOKEN = r'<\/?[^\s>]+'
REGEX_EMIT_TRAILING = r'\w+='
REGEX_EMIT_WORD = r'\w+'
REGEX_EMIT_END_TAG = r'>'

REGEX_SHEBANG_FULL = r'^#!\s*\S+'
REGEX_SHEBANG_WHITESPACE = r'\s+'
REGEX_SHEBANG_NON_WHITESPACE = r'\S+'


class Tokenizer(object):

    def __repr__(self):
        return '<Tokenizer>'

    @classmethod
    def tokenize(cls, data):
        """
        Public: Extract tokens from data

        data - String to tokenize

        Returns Array of token Strings.
        """
        return cls().extract_tokens(data)

    def extract_tokens(self, data):
        """
        Internal: Extract generic tokens from data.

        data - String to scan.

        Examples

          extract_tokens("printf('Hello')")
          # => ['printf', '(', ')']

        Returns Array of token Strings.
        """
        s = Scanner(data)
        tokens = []
        while not s.eos():
            if s.pos >= BYTE_LIMIT:
                break
            token = s.scan(REGEX_SHEBANG)
            if token:
                name = self.extract_shebang(token)
                if name:
                    tokens.append('SHEBANG#!%s' % name)
                continue

            # Single line comment
            if s.bol() and s.scan(START_SINGLE_LINE_COMMENT):
                s.skip_until(REGEX_BOL)
                continue

            # Multiline comments
            token = s.scan(START_MULTI_LINE_COMMENT)
            if token:
                close_token = MULTI_LINE_COMMENT_DICT[token]
                s.skip_until(close_token)
                continue

            # Skip single or double quoted strings
            if s.scan(REGEX_DOUBLE_QUOTE):
                if s.peek(1) == '"':
                    s.get(1)
                else:
                    s.skip_until(REGEX_DOUBLE_END_QUOTE)
                continue
            if s.scan(REGEX_SINGLE_QUOTE):
                if s.peek(1) == "'":
                    s.get(1)
                else:
                    s.skip_until(REGEX_SINGLE_END_QUOTE)
                continue

            # Skip number literals
            if s.scan(REGEX_NUMBER_LITERALS):
                continue

            # SGML style brackets
            token = s.scan(REGEX_SGML)
            if token:
                for t in self.extract_sgml_tokens(token):
                    tokens.append(t)
                continue

            # Common programming punctuation
            token = s.scan(REGEX_COMMON_PUNCTUATION)
            if token:
                tokens.append(token)
                continue

            # Regular token
            token = s.scan(REGEX_REGULAR_TOKEN)
            if token:
                tokens.append(token)
                continue

            # Common operators
            token = s.scan(REGEX_COMMON_OPERATORS)
            if token:
                tokens.append(token)
                continue

            s.get(1)
        return tokens

    @classmethod
    def extract_shebang(cls, data):
        """
        Internal: Extract normalized shebang command token.

        Examples

          extract_shebang("#!/usr/bin/ruby")
          # => "ruby"

          extract_shebang("#!/usr/bin/env node")
          # => "node"

        Returns String token or nil it couldn't be parsed.
        """
        s = Scanner(data)
        path = s.scan(REGEX_SHEBANG_FULL)
        if path:
            script = path.split('/')[-1]
            if script == 'env':
                s.scan(REGEX_SHEBANG_WHITESPACE)
                script = s.scan(REGEX_SHEBANG_NON_WHITESPACE)
            if script:
                script = compile(r'[^\d]+').match(script).group(0)
            return script
        return

    def extract_sgml_tokens(self, data):
        """
        Internal: Extract tokens from inside SGML tag.

        data - SGML tag String.

            Examples

              extract_sgml_tokens("<a href='' class=foo>")
              # => ["<a>", "href="]

        Returns Array of token Strings.
        """
        s = Scanner(data)
        tokens = []
        append = tokens.append

        while not s.eos():
            # Emit start token
            token = s.scan(REGEX_EMIT_START_TOKEN)
            if token:
                append(token + '>')
                continue

            # Emit attributes with trailing =
            token = s.scan(REGEX_EMIT_TRAILING)
            if token:
                append(token)

                # Then skip over attribute value
                if s.scan(REGEX_DOUBLE_QUOTE):
                    s.skip_until(REGEX_DOUBLE_END_QUOTE)
                    continue
                if s.scan(REGEX_SINGLE_QUOTE):
                    s.skip_until(REGEX_SINGLE_END_QUOTE)
                    continue
                s.skip_until(REGEX_EMIT_WORD)
                continue

            # Emit lone attributes
            token = s.scan(REGEX_EMIT_WORD)
            if token:
                append(token)

            # Stop at the end of the tag
            if s.scan(REGEX_EMIT_END_TAG):
                s.terminate()
                continue

            s.get()

        return tokens