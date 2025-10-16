#!/usr/bin/env python3
"""
Poistaa emojit kaikista Python-tiedostoista
"""

import os
import re

def remove_emojis_from_file(file_path):
    """Poistaa emojit yhdestä tiedostosta"""
    
    # Emoji-korvaukset
    emoji_replacements = {
        "🚀": "",
        "📁": "", 
        "✅": "",
        "📋": "",
        "📝": "",
        "📄": "",
        "🎉": "",
        "📂": "",
        "💡": "",
        "❌": "",
        "⏰": "",
        "🏗️": "",
        "📦": "",
        "➕": "",
        "💾": "",
        "🔄": "",
        "📊": "",
        "📈": "",
        "🔬": ""
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Korvaa emojit
        for emoji, replacement in emoji_replacements.items():
            content = content.replace(emoji + " ", replacement)
            content = content.replace(emoji, replacement)
        
        # Kirjoita takaisin jos muutoksia
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Poistettu emojit tiedostosta: {file_path}")
            return True
        else:
            print(f"Ei emojeja tiedostossa: {file_path}")
            return False
            
    except Exception as e:
        print(f"VIRHE käsiteltäessä {file_path}: {e}")
        return False

def main():
    """Käy läpi kaikki Python-tiedostot ja poistaa emojit"""
    
    python_files = [
        "test_step1.py",
        "test_step2.py", 
        "test_step3.py",
        "init_output_directory.py"
    ]
    
    modified_count = 0
    
    for file_name in python_files:
        if os.path.exists(file_name):
            if remove_emojis_from_file(file_name):
                modified_count += 1
        else:
            print(f"Tiedosto ei löydy: {file_name}")
    
    print(f"\nValmis! Muokattiin {modified_count} tiedostoa.")

if __name__ == "__main__":
    main()
