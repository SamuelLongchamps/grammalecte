from PySide.QtCore import QThread

import grammalecte.fr as gce
from grammalecte.fr.lexicographe import Lexicographe
from grammalecte.tokenizer import Tokenizer
from grammalecte.fr.textformatter import TextFormatter
import grammalecte.text as txt

gce.load()
gceDict = gce.getDictionary()
lexGraph = Lexicographe(gceDict)
tokenizerFr = Tokenizer("fr")
textFormatter = TextFormatter()


KEY_PARAGRAPH = "iParagraph"
KEY_GRAMMAR_ERROR = "lGrammarErrors"
KEY_SPELLING_ERROR = "lSpellingErrors"


def correctParagraph(paragraph, paragraphId):
    if not paragraph:
        return

    paragraph = textFormatter.formatText(paragraph)
    aGrammErrs = gce.parse(paragraph, "FR", False)
    aSpellErrs = []
    for token in tokenizerFr.genTokens(paragraph):
        if token['sType'] == "WORD" and \
                not gceDict.isValidToken(token['sValue']):
            aSpellErrs.append(token)

    return {
        KEY_PARAGRAPH: paragraphId,
        KEY_GRAMMAR_ERROR: aGrammErrs,
        KEY_SPELLING_ERROR: aSpellErrs
    }


def correct(text):
    correctedParagraphs = []
    iParagraph = 0
    for paragraph in txt.getParagraph(text):
        res = correctParagraph(paragraph, iParagraph)
        iParagraph += 1
        if res:
            correctedParagraphs.append(res)
    return correctedParagraphs


class CorrectThread(QThread):
    def __init__(self, text, callback):
        """
        :type text: str
        :type callback: (dict) -> None
        """
        QThread.__init__(self)
        self._text = text
        self._callback = callback

    def run(self):
        self._callback(correct(self._text))
        self.exec_()


def correctWithThread(text, callback):
    thread = CorrectThread(text, callback)
    thread.start()
    return thread