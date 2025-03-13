import re
from num2words import num2words

def translate_number_to_text(text):
    """Convert numbers to words in text"""
    text_separated = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    text_separated = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text_separated)
    
    def replace_number(match):
        number = match.group()
        return num2words(int(number), lang='en')
    
    return re.sub(r'\b\d+\b', replace_number, text_separated)

