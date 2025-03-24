#!/usr/bin/env python3

# Standard library imports
import os
import sys
import itertools
import threading
import time
import signal
import difflib
import warnings
from threading import Event
import re

# Third-party imports
import numpy as np
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup
import soundfile as sf
import sounddevice as sd
from kokoro_onnx import Kokoro
import pymupdf4llm
import fitz

warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')
warnings.filterwarnings("ignore", category=FutureWarning, module='ebooklib')

# Global flag to stop the spinner and audio
stop_spinner = False
stop_audio = False

def spinning_wheel(message="Processing...", progress=None):
    """Display a spinning wheel with a message."""
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    while not stop_spinner:
        spin = next(spinner)
        if progress is not None:
            sys.stdout.write(f"\r{message} {progress} {spin}")
        else:
            sys.stdout.write(f"\r{message} {spin}")
        sys.stdout.flush()
        time.sleep(0.1)
    # Clear the spinner line when done
    sys.stdout.write('\r' + ' ' * (len(message) + 50) + '\r')
    sys.stdout.flush()

def list_available_voices(kokoro):
    voices = list(kokoro.get_voices())
    print("Available voices:")
    for idx, voice in enumerate(voices):
        print(f"{idx + 1}. {voice}")
    return voices

def extract_text_from_epub(epub_file):
    book = epub.read_epub(epub_file)
    full_text = ""
    for item in book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            full_text += soup.get_text()
    return full_text

def chunk_text(text, initial_chunk_size=1000):
    """Split text into chunks at sentence boundaries with dynamic sizing."""
    sentences = text.replace('\n', ' ').split('.')
    chunks = []
    current_chunk = []
    current_size = 0
    chunk_size = initial_chunk_size
    
    for sentence in sentences:
        if not sentence.strip():
            continue  # Skip empty sentences
        
        sentence = sentence.strip() + '.'
        sentence_size = len(sentence)
        
        # If a single sentence is too long, split it into smaller pieces
        if sentence_size > chunk_size:
            words = sentence.split()
            current_piece = []
            current_piece_size = 0
            
            for word in words:
                word_size = len(word) + 1  # +1 for space
                if current_piece_size + word_size > chunk_size:
                    if current_piece:
                        chunks.append(' '.join(current_piece).strip() + '.')
                    current_piece = [word]
                    current_piece_size = word_size
                else:
                    current_piece.append(word)
                    current_piece_size += word_size
            
            if current_piece:
                chunks.append(' '.join(current_piece).strip() + '.')
            continue
        
        # Start new chunk if current one would be too large
        if current_size + sentence_size > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0
        
        current_chunk.append(sentence)
        current_size += sentence_size
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def validate_language(lang, kokoro):
    """Validate if the language is supported."""
    try:
        supported_languages = set(kokoro.get_languages())  # Get supported languages from Kokoro
        if lang not in supported_languages:
            supported_langs = ', '.join(sorted(supported_languages))
            raise ValueError(f"Unsupported language: {lang}\nSupported languages are: {supported_langs}")
        return lang
    except Exception as e:
        print(f"Error getting supported languages: {e}")
        sys.exit(1)

def print_usage():
    print("""
Usage: kokoro-tts <input_text_file> [<output_audio_file>] [options]

Commands:
    -h, --help         Show this help message
    --help-languages   List all supported languages
    --help-voices      List all available voices
    --merge-chunks     Merge existing chunks in split-output directory into chapter files

Options:
    --stream            Stream audio instead of saving to file
    --speed <float>     Set speech speed (default: 1.0)
    --lang <str>        Set language (default: en-us)
    --voice <str>       Set voice or blend voices (default: interactive selection)
    --split-output <dir> Save each chunk as separate file in directory
    --format <str>      Audio format: wav or mp3 (default: wav)
    --debug             Show detailed debug information

Input formats:
    .txt               Text file input
    .epub              EPUB book input (will process chapters)
    .pdf               PDF document input (extracts chapters from TOC or content)

Examples:
    kokoro-tts input.txt output.wav --speed 1.2 --lang en-us --voice af_sarah
    kokoro-tts input.epub --split-output ./chunks/ --format mp3
    kokoro-tts input.pdf output.wav --speed 1.2 --lang en-us --voice af_sarah
    kokoro-tts input.pdf --split-output ./chunks/ --format mp3
    kokoro-tts input.txt --stream --speed 0.8
    kokoro-tts input.txt output.wav --voice "af_sarah:60,am_adam:40"
    kokoro-tts input.txt --stream --voice "am_adam,af_sarah" # 50-50 blend
    kokoro-tts --merge-chunks --split-output ./chunks/ --format wav
    kokoro-tts --help-voices
    kokoro-tts --help-languages
    kokoro-tts input.epub --split-output ./chunks/ --debug
    """)

def print_supported_languages():
    """Print all supported languages from Kokoro."""
    try:
        kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
        languages = sorted(kokoro.get_languages())
        print("\nSupported languages:")
        for lang in languages:
            print(f"    {lang}")
        print()
    except Exception as e:
        print(f"Error loading model to get supported languages: {e}")
        sys.exit(1)

def print_supported_voices():
    """Print all supported voices from Kokoro."""
    try:
        kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
        voices = sorted(kokoro.get_voices())
        print("\nSupported voices:")
        for idx, voice in enumerate(voices):
            print(f"    {idx + 1}. {voice}")
        print()
    except Exception as e:
        print(f"Error loading model to get supported voices: {e}")
        sys.exit(1)

def validate_voice(voice, kokoro):
    """Validate if the voice is supported and handle voice blending.
    
    Format for blended voices: "voice1:weight,voice2:weight"
    Example: "af_sarah:60,am_adam:40" for 60-40 blend
    """
    try:
        supported_voices = set(kokoro.get_voices())
        
        # Parse comma seperated voices for blend
        if ',' in voice:
            voices = []
            weights = []
            
            # Parse voice:weight pairs
            for pair in voice.split(','):
                if ':' in pair:
                    v, w = pair.strip().split(':')
                    voices.append(v.strip())
                    weights.append(float(w.strip()))
                else:
                    voices.append(pair.strip())
                    weights.append(50.0)  # Default to 50% if no weight specified
            
            if len(voices) != 2:
                raise ValueError("voice blending needs two comma separated voices")
                 
            # Validate voice
            for v in voices:
                if v not in supported_voices:
                    supported_voices_list = ', '.join(sorted(supported_voices))
                    raise ValueError(f"Unsupported voice: {v}\nSupported voices are: {supported_voices_list}")
             
            # Normalize weights to sum to 100
            total = sum(weights)
            if total != 100:
                weights = [w * (100/total) for w in weights]
            
            # Create voice blend style
            style1 = kokoro.get_voice_style(voices[0])
            style2 = kokoro.get_voice_style(voices[1])
            blend = np.add(style1 * (weights[0]/100), style2 * (weights[1]/100))
            return blend
             
        # Single voice validation
        if voice not in supported_voices:
            supported_voices_list = ', '.join(sorted(supported_voices))
            raise ValueError(f"Unsupported voice: {voice}\nSupported voices are: {supported_voices_list}")
        return voice
    except Exception as e:
        print(f"Error getting supported voices: {e}")
        sys.exit(1)

def extract_chapters_from_epub(epub_file, debug=False):
    """Extract chapters from epub file using ebooklib's metadata and TOC."""
    if not os.path.exists(epub_file):
        raise FileNotFoundError(f"EPUB file not found: {epub_file}")
    
    book = epub.read_epub(epub_file)
    chapters = []
    
    if debug:
        print("\nBook Metadata:")
        for key, value in book.metadata.items():
            print(f"  {key}: {value}")
        
        print("\nTable of Contents:")
        def print_toc(items, depth=0):
            for item in items:
                indent = "  " * depth
                if isinstance(item, tuple):
                    section_title, section_items = item
                    print(f"{indent}• Section: {section_title}")
                    print_toc(section_items, depth + 1)
                elif isinstance(item, epub.Link):
                    print(f"{indent}• {item.title} -> {item.href}")
        print_toc(book.toc)
    
    def get_chapter_content(soup, start_id, next_id=None):
        """Extract content between two fragment IDs"""
        content = []
        start_elem = soup.find(id=start_id)
        
        if not start_elem:
            return ""
        
        # Skip the heading itself if it's a heading
        if start_elem.name in ['h1', 'h2', 'h3', 'h4']:
            current = start_elem.find_next_sibling()
        else:
            current = start_elem
            
        while current:
            # Stop if we hit the next chapter
            if next_id and current.get('id') == next_id:
                break
            # Stop if we hit another chapter heading
            if current.name in ['h1', 'h2', 'h3'] and 'chapter' in current.get_text().lower():
                break
            content.append(current.get_text())
            current = current.find_next_sibling()
            
        return '\n'.join(content).strip()
    
    def process_toc_items(items, depth=0):
        processed = []
        for i, item in enumerate(items):
            if isinstance(item, tuple):
                section_title, section_items = item
                if debug:
                    print(f"{'  ' * depth}Processing section: {section_title}")
                processed.extend(process_toc_items(section_items, depth + 1))
            elif isinstance(item, epub.Link):
                if debug:
                    print(f"{'  ' * depth}Processing link: {item.title} -> {item.href}")
                
                # Skip if title suggests it's front matter
                if (item.title.lower() in ['copy', 'copyright', 'title page', 'cover'] or
                    item.title.lower().startswith('by')):
                    continue
                
                # Extract the file name and fragment from href
                href_parts = item.href.split('#')
                file_name = href_parts[0]
                fragment_id = href_parts[1] if len(href_parts) > 1 else None
                
                # Find the document
                doc = next((doc for doc in book.get_items_of_type(ITEM_DOCUMENT) 
                          if doc.file_name.endswith(file_name)), None)
                
                if doc:
                    content = doc.get_content().decode('utf-8')
                    soup = BeautifulSoup(content, "html.parser")
                    
                    # If no fragment ID, get whole document content
                    if not fragment_id:
                        text_content = soup.get_text().strip()
                    else:
                        # Get the next fragment ID if available
                        next_item = items[i + 1] if i + 1 < len(items) else None
                        next_fragment = None
                        if isinstance(next_item, epub.Link):
                            next_href_parts = next_item.href.split('#')
                            if next_href_parts[0] == file_name and len(next_href_parts) > 1:
                                next_fragment = next_href_parts[1]
                        
                        # Extract content between fragments
                        text_content = get_chapter_content(soup, fragment_id, next_fragment)
                    
                    if text_content:
                        chapters.append({
                            'title': item.title,
                            'content': text_content,
                            'order': len(processed) + 1
                        })
                        processed.append(item)
                        if debug:
                            print(f"{'  ' * depth}Added chapter: {item.title}")
                            print(f"{'  ' * depth}Content length: {len(text_content)} chars")
                            print(f"{'  ' * depth}Word count: {len(text_content.split())}")
        return processed
    
    # Process the table of contents
    process_toc_items(book.toc)
    
    # If no chapters were found through TOC, try processing all documents
    if not chapters:
        if debug:
            print("\nNo chapters found in TOC, processing all documents...")
        
        # Get all document items sorted by file name
        docs = sorted(
            book.get_items_of_type(ITEM_DOCUMENT),
            key=lambda x: x.file_name
        )
        
        for doc in docs:
            if debug:
                print(f"Processing document: {doc.file_name}")
            
            content = doc.get_content().decode('utf-8')
            soup = BeautifulSoup(content, "html.parser")
            
            # Try to find chapter divisions
            chapter_divs = soup.find_all(['h1', 'h2', 'h3'], class_=lambda x: x and 'chapter' in x.lower())
            if not chapter_divs:
                chapter_divs = soup.find_all(lambda tag: tag.name in ['h1', 'h2', 'h3'] and 
                                          ('chapter' in tag.get_text().lower() or
                                           'book' in tag.get_text().lower()))
            
            if chapter_divs:
                # Process each chapter division
                for i, div in enumerate(chapter_divs):
                    title = div.get_text().strip()
                    
                    # Get content until next chapter heading or end
                    content = ''
                    for tag in div.find_next_siblings():
                        if tag.name in ['h1', 'h2', 'h3'] and (
                            'chapter' in tag.get_text().lower() or
                            'book' in tag.get_text().lower()):
                            break
                        content += tag.get_text() + '\n'
                    
                    if content.strip():
                        chapters.append({
                            'title': title,
                            'content': content.strip(),
                            'order': len(chapters) + 1
                        })
                        if debug:
                            print(f"Added chapter: {title}")
            else:
                # No chapter divisions found, treat whole document as one chapter
                text_content = soup.get_text().strip()
                if text_content:
                    # Try to find a title
                    title_tag = soup.find(['h1', 'h2', 'title'])
                    title = title_tag.get_text().strip() if title_tag else f"Chapter {len(chapters) + 1}"
                    
                    if title.lower() not in ['copy', 'copyright', 'title page', 'cover']:
                        chapters.append({
                            'title': title,
                            'content': text_content,
                            'order': len(chapters) + 1
                        })
                        if debug:
                            print(f"Added chapter: {title}")
    
    # Print summary
    if chapters:
        print("\nSuccessfully extracted {} chapters:".format(len(chapters)))
        for chapter in chapters:
            print(f"  {chapter['order']}. {chapter['title']}")
        
        total_words = sum(len(chapter['content'].split()) for chapter in chapters)
        print("\nBook Summary:")
        print(f"Total Chapters: {len(chapters)}")
        print(f"Total Words: {total_words:,}")
        print(f"Total Duration: {total_words / 150:.1f} minutes")
        
        if debug:
            print("\nDetailed Chapter List:")
            for chapter in chapters:
                word_count = len(chapter['content'].split())
                print(f"  • {chapter['title']}")
                print(f"    Words: {word_count:,}")
                print(f"    Duration: {word_count / 150:.1f} minutes")
    else:
        print("\nWarning: No chapters were extracted!")
        if debug:
            print("\nAvailable documents:")
            for doc in book.get_items_of_type(ITEM_DOCUMENT):
                print(f"  • {doc.file_name}")
    
    return chapters

class PdfParser:
    """Parser for extracting chapters from PDF files.
    
    Attempts to extract chapters first from table of contents,
    then falls back to markdown-based extraction if TOC fails.
    """
    
    def __init__(self, pdf_path: str, debug: bool = False, min_chapter_length: int = 50):
        """Initialize PDF parser.
        
        Args:
            pdf_path: Path to PDF file
            debug: Enable debug logging
            min_chapter_length: Minimum text length to consider as chapter
        """
        self.pdf_path = pdf_path
        self.chapters = []
        self.debug = debug
        self.min_chapter_length = min_chapter_length
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    def get_chapters(self):
        """Extract chapters from PDF file.
        
        Returns:
            List of chapter dictionaries with title, content and order.
        """
        if self.debug:
            print("\nDEBUG: Starting chapter extraction...")
            print(f"DEBUG: PDF file: {self.pdf_path}")
            print(f"DEBUG: Min chapter length: {self.min_chapter_length}")
        
        # Try TOC extraction first
        if self.get_chapters_from_toc():
            if self.debug:
                print(f"\nDEBUG: Successfully extracted {len(self.chapters)} chapters from TOC")
            return self.chapters
            
        # Fall back to markdown extraction
        if self.debug:
            print("\nDEBUG: TOC extraction failed, trying markdown conversion...")
        
        self.chapters = self.get_chapters_from_markdown()
        
        if self.debug:
            print(f"\nDEBUG: Markdown extraction complete")
            print(f"DEBUG: Found {len(self.chapters)} chapters")
            
        return self.chapters

    def get_chapters_from_toc(self):
        """Extract chapters using PDF table of contents.
        
        Returns:
            bool: True if chapters were found, False otherwise
        """
        doc = None
        try:
            doc = fitz.open(self.pdf_path)
            toc = doc.get_toc()
            
            if not toc:
                if self.debug:
                    print("\nDEBUG: No table of contents found")
                return False

            # Print TOC structure
            print("\nTable of Contents:")
            for level, title, page in toc:
                title = self._clean_title(title)
                indent = "  " * (level - 1)
                print(f"{indent}{'•' if level > 1 else '>'} {title} (page {page})")
            
            if self.debug:
                print(f"\nDEBUG: Found {len(toc)} TOC entries")
            
            # Get user confirmation
            print("\nPress Enter to start processing, or Ctrl+C to cancel...")
            input()
            
            # Extract level 1 chapters, filtering out empty titles and duplicates
            seen_pages = set()
            chapter_markers = []
            
            for level, title, page in toc:
                if level == 1:
                    title = self._clean_title(title)
                    # Skip empty titles or titles that start on same page as previous entry
                    if title and page not in seen_pages:
                        chapter_markers.append((title, page))
                        seen_pages.add(page)
            
            if not chapter_markers:
                if self.debug:
                    print("\nDEBUG: No level 1 chapters found in TOC")
                return False
            
            if self.debug:
                print(f"\nDEBUG: Found {len(chapter_markers)} chapters:")
                for title, page in chapter_markers:
                    print(f"DEBUG: • {title} (page {page})")
            
            # Process each chapter
            for i, (title, start_page) in enumerate(chapter_markers):
                if self.debug:
                    print(f"\nDEBUG: Processing chapter {i+1}/{len(chapter_markers)}")
                    print(f"DEBUG: Title: {title}")
                    print(f"DEBUG: Start page: {start_page}")
                
                # Get chapter end page
                end_page = (chapter_markers[i + 1][1] - 1 
                           if i < len(chapter_markers) - 1 
                           else doc.page_count)
                
                # Extract chapter text
                chapter_text = self._extract_chapter_text(doc, start_page - 1, end_page)
                
                if len(chapter_text.strip()) > self.min_chapter_length:
                    self.chapters.append({
                        'title': title,
                        'content': chapter_text,
                        'order': i + 1
                    })
                    if self.debug:
                        print(f"DEBUG: Added chapter with {len(chapter_text.split())} words")
            
            return bool(self.chapters)
            
        except Exception as e:
            if self.debug:
                print(f"\nDEBUG: Error in TOC extraction: {str(e)}")
            return False
            
        finally:
            if doc:
                doc.close()

    def get_chapters_from_markdown(self):
        """Extract chapters by converting PDF to markdown.
        
        Returns:
            List of chapter dictionaries
        """
        chapters = []
        try:
            def progress(current, total):
                if self.debug:
                    print(f"\rConverting page {current}/{total}...", end="", flush=True)
            
            # Convert PDF to markdown
            md_text = pymupdf4llm.to_markdown(
                self.pdf_path,
                show_progress=True,
                progress_callback=progress
            )
            
            # Clean up markdown text
            md_text = self._clean_markdown(md_text)
            
            # Extract chapters
            current_chapter = None
            current_text = []
            chapter_count = 0
            
            for line in md_text.split('\n'):
                if line.startswith('#'):
                    # Save previous chapter if exists
                    if current_chapter and current_text:
                        chapter_text = ''.join(current_text)
                        if len(chapter_text.strip()) > self.min_chapter_length:
                            chapters.append({
                                'title': current_chapter,
                                'content': chapter_text,
                                'order': chapter_count
                            })
                    
                    # Start new chapter
                    chapter_count += 1
                    current_chapter = f"Chapter {chapter_count}_{line.lstrip('#').strip()}"
                    current_text = []
                else:
                    if current_chapter is not None:
                        current_text.append(line + '\n')
            
            # Add final chapter
            if current_chapter and current_text:
                chapter_text = ''.join(current_text)
                if len(chapter_text.strip()) > self.min_chapter_length:
                    chapters.append({
                        'title': current_chapter,
                        'content': chapter_text,
                        'order': chapter_count
                    })
            
            return chapters
            
        except Exception as e:
            if self.debug:
                print(f"\nDEBUG: Error in markdown extraction: {str(e)}")
            return chapters

    def _clean_title(self, title: str) -> str:
        """Clean up chapter title text."""
        return title.strip().replace('\u200b', ' ')
        
    def _clean_markdown(self, text: str) -> str:
        """Clean up converted markdown text."""
        # Remove page markers
        text = text.replace('-', '')
        # Remove other unwanted characters
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
        
    def _extract_chapter_text(self, doc, start_page: int, end_page: int) -> str:
        """Extract text from PDF pages."""
        chapter_text = []
        for page_num in range(start_page, end_page):
            try:
                page = doc[page_num]
                text = page.get_text()
                chapter_text.append(text)
            except Exception as e:
                if self.debug:
                    print(f"\nDEBUG: Error extracting page {page_num}: {str(e)}")
                continue
                
        return '\n'.join(chapter_text)

def process_chunk_sequential(chunk: str, kokoro: Kokoro, voice: str, speed: float, lang: str, 
                           retry_count=0, debug=False) -> tuple[list[float] | None, int | None]:
    """Process a single chunk of text sequentially with automatic chunk size adjustment."""
    try:
        if debug:
            sys.stdout.write("\033[K")  # Clear to end of line
            sys.stdout.write(f"\nDEBUG: Processing chunk of length {len(chunk)}")
            if retry_count > 0:
                sys.stdout.write(f"\nDEBUG: Retry #{retry_count} - Reduced chunk size to {len(chunk)}")
            sys.stdout.write("\n")  # Move back to progress line
            sys.stdout.flush()
        
        samples, sample_rate = kokoro.create(chunk, voice=voice, speed=speed, lang=lang)
        return samples, sample_rate
    except Exception as e:
        error_msg = str(e)
        if "index 510 is out of bounds" in error_msg:
            current_size = len(chunk)
            new_size = int(current_size * 0.6)  # Reduce by 40% to converge faster
            
            if debug:
                sys.stdout.write("\033[K")  # Clear to end of line
                sys.stdout.write(f"\nDEBUG: Phoneme length error detected on chunk size {current_size}")
                sys.stdout.write(f"\nDEBUG: Attempting retry with size {new_size}")
                sys.stdout.write("\n")
            else:
                # Show a user-friendly message in non-debug mode
                sys.stdout.write("\033[K")  # Clear to end of line
                sys.stdout.write("\rNote: Automatically handling a long text segment...")
                sys.stdout.write("\n")
            sys.stdout.flush()
            
            # Split this chunk into smaller pieces
            words = chunk.split()
            current_piece = []
            current_size = 0
            pieces = []
            
            for word in words:
                word_size = len(word) + 1  # +1 for space
                if current_size + word_size > new_size:
                    if current_piece:
                        pieces.append(' '.join(current_piece).strip())
                    current_piece = [word]
                    current_size = word_size
                else:
                    current_piece.append(word)
                    current_size += word_size
            
            if current_piece:
                pieces.append(' '.join(current_piece).strip())
            
            if debug:
                sys.stdout.write("\033[K")
                sys.stdout.write(f"\nDEBUG: Split chunk into {len(pieces)} pieces")
                for i, piece in enumerate(pieces, 1):
                    sys.stdout.write(f"\nDEBUG: Piece {i} length: {len(piece)}")
                sys.stdout.write("\n")
                sys.stdout.flush()
            
            # Process each piece
            all_samples = []
            last_sample_rate = None
            
            for i, piece in enumerate(pieces, 1):
                if debug:
                    sys.stdout.write("\033[K")
                    sys.stdout.write(f"\nDEBUG: Processing piece {i}/{len(pieces)}")
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                
                samples, sr = process_chunk_sequential(piece, kokoro, voice, speed, lang, 
                                                     retry_count + 1, debug)
                if samples is not None:
                    all_samples.extend(samples)
                    last_sample_rate = sr
            
            if all_samples:
                if debug:
                    sys.stdout.write("\033[K")
                    sys.stdout.write(f"\nDEBUG: Successfully processed all {len(pieces)} pieces")
                    sys.stdout.write("\n")
                sys.stdout.flush()
                return all_samples, last_sample_rate
            
            if debug:
                sys.stdout.write("\033[K")
                sys.stdout.write(f"\nDEBUG: Failed to process any pieces after splitting")
                sys.stdout.write("\n")
            sys.stdout.flush()
            
        # Show a more user-friendly error message in non-debug mode
        if not debug:
            sys.stdout.write("\033[K")
            sys.stdout.write(f"\rError: Unable to process text segment. Try using smaller chunks or enable debug mode for details.")
        else:
            sys.stdout.write("\033[K")
            sys.stdout.write(f"\nError processing chunk: {e}")
            sys.stdout.write(f"\nDEBUG: Full error message: {error_msg}")
            sys.stdout.write(f"\nDEBUG: Chunk length: {len(chunk)}")
        sys.stdout.write("\n")
        sys.stdout.flush()
        
        return None, None

def convert_text_to_audio(input_file, output_file=None, voice=None, speed=1.0, lang="en-us", 
                         stream=False, split_output=None, format="wav", debug=False):
    global stop_spinner
    # Load Kokoro model
    try:
        kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")

        # Validate language after loading model
        lang = validate_language(lang, kokoro)
        
        # Handle voice selection
        if voice:
            voice = validate_voice(voice, kokoro)
        else:
            # Interactive voice selection
            voices = list_available_voices(kokoro)
            print("\nHow to choose a voice:")
            print("You can use either a single voice or blend two voices together.")
            print("\nFor a single voice:")
            print("  • Just enter one number (example: '7')")
            print("\nFor blending two voices:")
            print("  • Enter two numbers separated by comma")
            print("  • Optionally add weights after each number using ':weight'")
            print("\nExamples:")
            print("  • '7'      - Use voice #7 only")
            print("  • '7,11'   - Mix voices #7 and #11 equally (50% each)")
            print("  • '7:60,11:40' - Mix 60% of voice #7 with 40% of voice #11")
            try:
                voice_input = input("Choose voice(s) by number: ")
                if ',' in voice_input:
                    # Handle blended voices
                    pairs = []
                    for pair in voice_input.split(','):
                        if ':' in pair:
                            num, weight = pair.strip().split(':')
                            voice_idx = int(num.strip()) - 1
                            if not (0 <= voice_idx < len(voices)):
                                raise ValueError(f"Invalid voice number: {int(num)}")
                            pairs.append(f"{voices[voice_idx]}:{weight}")
                        else:
                            voice_idx = int(pair.strip()) - 1
                            if not (0 <= voice_idx < len(voices)):
                                raise ValueError(f"Invalid voice number: {int(pair)}")
                            pairs.append(voices[voice_idx])
                    voice = ','.join(pairs)
                else:
                    # Single voice
                    voice_choice = int(voice_input) - 1
                    if not (0 <= voice_choice < len(voices)):
                        raise ValueError("Invalid choice")
                    voice = voices[voice_choice]
                # Validate and potentially convert to blend
                voice = validate_voice(voice, kokoro)
            except (ValueError, IndexError):
                print("Invalid choice. Using default voice.")
                voice = "af_sarah"  # default voice
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading Kokoro model: {e}")
        sys.exit(1)
    
    # Read the input file (handle .txt or .epub)
    if input_file.endswith('.epub'):
        chapters = extract_chapters_from_epub(input_file, debug)
        if not chapters:
            print("No chapters found in EPUB file.")
            sys.exit(1)
            
            print("\nPress Enter to start processing, or Ctrl+C to cancel...")
            input()
            
            if split_output:
                os.makedirs(split_output, exist_ok=True)
                
                # First create all chapter directories and info files
                print("\nCreating chapter directories and info files...")
                for chapter_num, chapter in enumerate(chapters, 1):
                    chapter_dir = os.path.join(split_output, f"chapter_{chapter_num:03d}")
                    os.makedirs(chapter_dir, exist_ok=True)
                    
                    # Write chapter info with more details
                    info_file = os.path.join(chapter_dir, "info.txt")
                    with open(info_file, "w", encoding="utf-8") as f:
                        f.write(f"Title: {chapter['title']}\n")
                        f.write(f"Order: {chapter['order']}\n")
                        f.write(f"Words: {len(chapter['content'].split())}\n")
                        f.write(f"Estimated Duration: {len(chapter['content'].split()) / 150:.1f} minutes\n")
                
                print("Created chapter directories and info files")
                
                # Continue with existing processing code...
    elif input_file.endswith('.pdf'):
        parser = PdfParser(input_file, debug=debug)
        chapters = parser.get_chapters()
    else:
        with open(input_file, 'r', encoding='utf-8') as file:
            text = file.read()
        # Treat single text file as one chapter
        chapters = [{'title': 'Chapter 1', 'content': text}]

    if stream:
        import asyncio
        # Stream each chapter
        for chapter in chapters:
            print(f"\nStreaming: {chapter['title']}")
            chunks = chunk_text(chapter['content'], initial_chunk_size=1000)
            asyncio.run(stream_audio(kokoro, chapter['content'], voice, speed, lang, debug))
    else:
        if split_output:
            os.makedirs(split_output, exist_ok=True)
            
            for chapter_num, chapter in enumerate(chapters, 1):
                chapter_dir = os.path.join(split_output, f"chapter_{chapter_num:03d}")
                
                # Skip if chapter is already fully processed
                if os.path.exists(chapter_dir):
                    info_file = os.path.join(chapter_dir, "info.txt")
                    if os.path.exists(info_file):
                        chunks = chunk_text(chapter['content'], initial_chunk_size=1000)
                        total_chunks = len(chunks)
                        existing_chunks = len([f for f in os.listdir(chapter_dir) 
                                            if f.startswith("chunk_") and f.endswith(f".{format}")])
                        
                        if existing_chunks == total_chunks:
                            print(f"\nSkipping {chapter['title']}: Already completed ({existing_chunks} chunks)")
                            continue
                        else:
                            print(f"\nResuming {chapter['title']}: Found {existing_chunks}/{total_chunks} chunks")

                print(f"\nProcessing: {chapter['title']}")
                os.makedirs(chapter_dir, exist_ok=True)
                
                # Write chapter info if not exists
                info_file = os.path.join(chapter_dir, "info.txt")
                if not os.path.exists(info_file):
                    with open(info_file, "w", encoding="utf-8") as f:
                        f.write(f"Title: {chapter['title']}\n")
                
                chunks = chunk_text(chapter['content'], initial_chunk_size=1000)
                total_chunks = len(chunks)
                processed_chunks = len([f for f in os.listdir(chapter_dir) 
                                     if f.startswith("chunk_") and f.endswith(f".{format}")])
                
                for chunk_num, chunk in enumerate(chunks, 1):
                    if stop_audio:  # Check for interruption
                        break
                    
                    # Skip if chunk file already exists (regardless of position)
                    chunk_file = os.path.join(chapter_dir, f"chunk_{chunk_num:03d}.{format}")
                    if os.path.exists(chunk_file):
                        continue  # Don't increment processed_chunks here since we counted them above
                    
                    # Create progress bar
                    filled = "■" * processed_chunks
                    remaining = "□" * (total_chunks - processed_chunks)
                    progress_bar = f"[{filled}{remaining}] ({processed_chunks}/{total_chunks})"
                    
                    stop_spinner = False
                    spinner_thread = threading.Thread(
                        target=spinning_wheel,
                        args=(f"Processing {chapter['title']}", progress_bar)
                    )
                    spinner_thread.start()
                    
                    try:
                        samples, sample_rate = process_chunk_sequential(
                            chunk, kokoro, voice, speed, lang, 
                            retry_count=0, debug=debug  # Add retry parameters
                        )
                        if samples is not None:
                            sf.write(chunk_file, samples, sample_rate)
                            processed_chunks += 1
                    except Exception as e:
                        print(f"\nError processing chunk {chunk_num}: {e}")
                    
                    stop_spinner = True
                    spinner_thread.join()
                    
                    if stop_audio:  # Check for interruption
                        break
                
                print(f"\nCompleted {chapter['title']}: {processed_chunks}/{total_chunks} chunks processed")
                
                if stop_audio:  # Check for interruption
                    break
            
            print(f"\nCreated audio files for {len(chapters)} chapters in {split_output}/")
        else:
            # Combine all chapters into one file
            all_samples = []
            sample_rate = None
            
            for chapter_num, chapter in enumerate(chapters, 1):
                print(f"\nProcessing: {chapter['title']}")
                chunks = chunk_text(chapter['content'], initial_chunk_size=1000)
                processed_chunks = 0
                total_chunks = len(chunks)
                
                for chunk_num, chunk in enumerate(chunks, 1):
                    if stop_audio:  # Check for interruption
                        break
                    
                    stop_spinner = False
                    spinner_thread = threading.Thread(
                        target=spinning_wheel,
                        args=(f"Processing chunk {chunk_num}/{total_chunks}",)
                    )
                    spinner_thread.start()
                    
                    try:
                        samples, sr = process_chunk_sequential(
                            chunk, kokoro, voice, speed, lang,
                            retry_count=0, debug=debug  # Add retry parameters
                        )
                        if samples is not None:
                            if sample_rate is None:
                                sample_rate = sr
                            all_samples.extend(samples)
                            processed_chunks += 1
                    except Exception as e:
                        print(f"\nError processing chunk {chunk_num}: {e}")
                    
                    stop_spinner = True
                    spinner_thread.join()
                
                print(f"\nCompleted {chapter['title']}: {processed_chunks}/{total_chunks} chunks processed")
            
            if all_samples:
                print("\nSaving complete audio file...")
                if not output_file:
                    output_file = f"{os.path.splitext(input_file)[0]}.{format}"
                sf.write(output_file, all_samples, sample_rate)
                print(f"Created {output_file}")

async def stream_audio(kokoro, text, voice, speed, lang, debug=False):
    global stop_spinner, stop_audio
    stop_spinner = False
    stop_audio = False
    
    print("Starting audio stream...")
    chunks = chunk_text(text, initial_chunk_size=1000)
    
    for i, chunk in enumerate(chunks, 1):
        if stop_audio:
            break
        # Update progress percentage
        progress = int((i / len(chunks)) * 100)
        spinner_thread = threading.Thread(
            target=spinning_wheel, 
            args=(f"Streaming chunk {i}/{len(chunks)}",)
        )
        spinner_thread.start()
        
        async for samples, sample_rate in kokoro.create_stream(
            chunk, voice=voice, speed=speed, lang=lang
        ):
            if stop_audio:
                break
            if debug:
                print(f"\nDEBUG: Playing chunk of {len(samples)} samples")
            sd.play(samples, sample_rate)
            sd.wait()
        
        stop_spinner = True
        spinner_thread.join()
        stop_spinner = False
    
    print("\nStreaming completed.")

def handle_ctrl_c(signum, frame):
    global stop_spinner, stop_audio
    print("\nCtrl+C detected, stopping...")
    stop_spinner = True
    stop_audio = True
    sys.exit(0)

# Register the signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, handle_ctrl_c)

def merge_chunks_to_chapters(split_output_dir, format="wav"):
    """Merge audio chunks into complete chapter files."""
    global stop_spinner

    if not os.path.exists(split_output_dir):
        print(f"Error: Directory {split_output_dir} does not exist.")
        return

    # Find all chapter directories
    chapter_dirs = sorted([d for d in os.listdir(split_output_dir) 
                          if d.startswith("chapter_") and os.path.isdir(os.path.join(split_output_dir, d))])

    if not chapter_dirs:
        print(f"No chapter directories found in {split_output_dir}")
        return

    # Track used titles to handle duplicates
    used_titles = set()

    for chapter_dir in chapter_dirs:
        chapter_path = os.path.join(split_output_dir, chapter_dir)
        chunk_files = sorted([f for f in os.listdir(chapter_path) 
                            if f.startswith("chunk_") and f.endswith(f".{format}")])
        
        if not chunk_files:
            print(f"No chunks found in {chapter_dir}")
            continue

        # Read chapter title from info.txt if available
        chapter_title = chapter_dir
        info_file = os.path.join(chapter_path, "info.txt")
        if os.path.exists(info_file):
            with open(info_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith("Title:"):
                        chapter_title = line.replace("Title:", "").strip()
                        break

        # Clean title for filesystem use
        safe_title = "".join(c for c in chapter_title if c.isalnum() or c in (' ', '-', '_')).strip()
        
        # Handle duplicate or empty titles
        if not safe_title or safe_title in used_titles:
            merged_file = os.path.join(split_output_dir, f"{chapter_dir}.{format}")
        else:
            merged_file = os.path.join(split_output_dir, f"{safe_title}.{format}")
            used_titles.add(safe_title)

        print(f"\nMerging chunks for {chapter_title}")
        
        # Initialize variables for merging
        all_samples = []
        sample_rate = None
        total_duration = 0
        
        # Create progress spinner
        total_chunks = len(chunk_files)
        processed_chunks = 0
        
        for chunk_file in chunk_files:
            chunk_path = os.path.join(chapter_path, chunk_file)
            
            # Display progress
            print(f"\rProcessing chunk {processed_chunks + 1}/{total_chunks}", end="")
            
            try:
                # Read audio data
                data, sr = sf.read(chunk_path)
                
                # Verify the audio data
                if len(data) == 0:
                    print(f"\nWarning: Empty audio data in {chunk_file}")
                    continue
                
                # Initialize sample rate or verify it matches
                if sample_rate is None:
                    sample_rate = sr
                elif sr != sample_rate:
                    print(f"\nWarning: Sample rate mismatch in {chunk_file}")
                    continue
                
                # Add chunk duration to total
                chunk_duration = len(data) / sr
                total_duration += chunk_duration
                
                # Append the audio data
                all_samples.extend(data)
                processed_chunks += 1
                
            except Exception as e:
                print(f"\nError processing {chunk_file}: {e}")
        
        print()  # New line after progress
        
        if all_samples:
            print(f"Saving merged chapter to {merged_file}")
            print(f"Total duration: {total_duration:.2f} seconds")
            
            try:
                # Ensure all_samples is a numpy array
                all_samples = np.array(all_samples)
                
                # Save merged audio
                sf.write(merged_file, all_samples, sample_rate)
                print(f"Successfully merged {processed_chunks}/{total_chunks} chunks")
                
                # Verify the output file
                if os.path.exists(merged_file):
                    output_data, output_sr = sf.read(merged_file)
                    output_duration = len(output_data) / output_sr
                    print(f"Verified output file: {output_duration:.2f} seconds")
                else:
                    print("Warning: Output file was not created")
                
            except Exception as e:
                print(f"Error saving merged file: {e}")
        else:
            print("No valid audio data to merge")

def get_valid_options():
    """Return a set of valid command line options"""
    return {
        '-h', '--help',
        '--help-languages',
        '--help-voices',
        '--merge-chunks',
        '--stream',
        '--speed',
        '--lang',
        '--voice',
        '--split-output',
        '--format',
        '--debug'  # Add debug option
    }

if __name__ == "__main__":
    # Validate command line options first
    valid_options = get_valid_options()
    unknown_options = []
    
    # Check for unknown options
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith('--') or arg.startswith('-'):
            # Check if it's a valid option
            if arg not in valid_options:
                unknown_options.append(arg)
            # Skip the next argument if it's a value for an option that takes parameters
            elif arg in {'--speed', '--lang', '--voice', '--split-output', '--format'}:
                i += 1
        i += 1
    
    # If unknown options were found, show error and help
    if unknown_options:
        print("Error: Unknown option(s):", ", ".join(unknown_options))
        print("\nDid you mean one of these?")
        for unknown in unknown_options:
            # Find similar valid options using string similarity
            similar = difflib.get_close_matches(unknown, valid_options, n=3, cutoff=0.4)
            if similar:
                print(f"  {unknown} -> {', '.join(similar)}")
        print("\n")  # Add extra newline for spacing
        print_usage()  # Show the full help text
        sys.exit(1)
    
    # Handle help commands first
    if len(sys.argv) == 2:
        if sys.argv[1] in ['-h', '--help']:
            print_usage()
            sys.exit(0)
        elif sys.argv[1] == '--help-languages':
            print_supported_languages()
            sys.exit(0)
        elif sys.argv[1] == '--help-voices':
            print_supported_voices()
            sys.exit(0)
    
    # Parse arguments
    input_file = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
    else:
        output_file = None

    stream = '--stream' in sys.argv
    speed = 1.0  # default speed
    lang = "en-us"  # default language
    voice = None  # default to interactive selection
    split_output = None
    format = "wav"  # default format
    merge_chunks = '--merge-chunks' in sys.argv
    
    # Parse optional arguments
    for i, arg in enumerate(sys.argv):
        if arg == '--speed' and i + 1 < len(sys.argv):
            try:
                speed = float(sys.argv[i + 1])
            except ValueError:
                print("Error: Speed must be a number")
                sys.exit(1)
        elif arg == '--lang' and i + 1 < len(sys.argv):
            lang = sys.argv[i + 1]
        elif arg == '--voice' and i + 1 < len(sys.argv):
            voice = sys.argv[i + 1]
        elif arg == '--split-output' and i + 1 < len(sys.argv):
            split_output = sys.argv[i + 1]
        elif arg == '--format' and i + 1 < len(sys.argv):
            format = sys.argv[i + 1].lower()
            if format not in ['wav', 'mp3']:
                print("Error: Format must be either 'wav' or 'mp3'")
                sys.exit(1)
    
    # Handle merge chunks operation
    if merge_chunks:
        if not split_output:
            print("Error: --split-output directory must be specified when using --merge-chunks")
            sys.exit(1)
        merge_chunks_to_chapters(split_output, format)
        sys.exit(0)
    
    # Normal processing mode
    if not input_file:
        print("Error: Input file required for text-to-speech conversion")
        print_usage()
        sys.exit(1)

    # Ensure the input file exists
    if not os.access(input_file, os.R_OK):
        print(f"Error: Cannot read from {input_file}. File may not exist or you may not have permission to read it.")
        sys.exit(1)
    
    # Ensure the output file has a proper extension if specified
    if output_file and not output_file.endswith(('.' + format)):
        print(f"Error: Output file must have .{format} extension.")
        sys.exit(1)
    
    # Add debug flag
    debug = '--debug' in sys.argv
    
    # Convert text to audio with debug flag
    convert_text_to_audio(input_file, output_file, voice=voice, stream=stream, 
                         speed=speed, lang=lang, split_output=split_output, 
                         format=format, debug=debug)

