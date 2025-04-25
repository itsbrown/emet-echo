import nltk
import ssl
import logging
import re
import html
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from heapq import nlargest

# Set up logging
logger = logging.getLogger(__name__)

# Download NLTK resources - handle SSL issues gracefully
try:
    # Set up SSL context for downloads
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    
    # Download required NLTK data
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('stopwords')
    print("Successfully downloaded NLTK resources")
except Exception as e:
    logger.error(f"Failed to download NLTK resources: {str(e)}")
    print(f"Failed to download NLTK resources: {str(e)}")
    
# Verify NLTK resources are available
required_resources = [
    ('tokenizers/punkt', 'punkt'),
    ('tokenizers/punkt_tab', 'punkt_tab'),
    ('corpora/stopwords', 'stopwords')
]

for resource_path, resource_name in required_resources:
    try:
        nltk.data.find(resource_path)
        print(f"NLTK resource {resource_name} is available")
    except LookupError:
        print(f"NLTK resource {resource_name} is NOT available")
        logger.warning(f"NLTK resource {resource_name} is not available")

def clean_html(text):
    """
    Remove HTML tags and entities from text
    
    Args:
        text: Text that may contain HTML
        
    Returns:
        Clean plain text without HTML
    """
    if not text:
        return ""
        
    # First, decode HTML entities
    text = html.unescape(text)
    
    # Remove HTML tags (this pattern matches both opening and closing tags)
    text = re.sub(r'<[^>]*>', ' ', text)
    
    # Remove any leftover HTML-like content
    text = re.sub(r'&[a-zA-Z0-9]+;', ' ', text)
    
    # Fix URL issues in text (often found in Federal Register documents)
    text = re.sub(r'\[www\.gpo\.gov\]', '', text)
    text = re.sub(r'\[\s*([^\]]+)\s*\]', r'\1', text)
    
    # Remove common Federal Register header/footer content
    text = re.sub(r'Federal Register[^\n]*\n', '', text)
    text = re.sub(r'Presidential Documents[^\n]*\n', '', text)
    text = re.sub(r'FR Doc[^\n]*\n', '', text)
    text = re.sub(r'Volume \d+[^\n]*\n', '', text)
    text = re.sub(r'Pages \d+-\d+[^\n]*\n', '', text)
    
    # Fix spacing issues
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def generate_summary(text, num_sentences=3, style="standard"):
    """
    Generate a summary of the given text using extractive summarization
    
    Args:
        text: The text to summarize
        num_sentences: Number of sentences in the summary (default: 3)
        style: Summary style - "standard", "journalist", or "twitter" (default: "standard")
        
    Returns:
        A summary of the text in the specified style
    """
    if not text or text == "Content not available":
        return "Summary not available."
    
    # Clean any HTML from the input text
    cleaned_text = clean_html(text)
    
    # If cleaning removed too much content, use original text as fallback
    if len(cleaned_text) < 100 and len(text) > 100:
        logger.warning("HTML cleaning removed too much content, using original text")
        cleaned_text = text
    
    # Delegate to the appropriate summary function based on style
    try:
        if style == "journalist":
            return generate_journalist_summary(cleaned_text, num_sentences)
        elif style == "twitter":
            return generate_twitter_summary(cleaned_text)
        else:
            # Standard extractive summary
            return generate_extractive_summary(cleaned_text, num_sentences)
    except Exception as e:
        logger.error(f"Error generating {style} summary: {str(e)}")
        return "Unable to generate summary."

def generate_extractive_summary(text, num_sentences=3):
    """
    Generate a summary using extractive summarization (original algorithm)
    
    Args:
        text: The text to summarize
        num_sentences: Number of sentences in the summary
        
    Returns:
        An extractive summary of the text
    """
    try:
        # Tokenize the text into sentences
        sentences = sent_tokenize(text)
        
        # If text is too short, return it as is
        if len(sentences) <= num_sentences:
            return text
        
        # Get stopwords
        try:
            stop_words = set(stopwords.words('english'))
        except:
            # Fallback if NLTK stopwords not available
            stop_words = set(['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 
                            'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 
                            'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 
                            "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 
                            'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 
                            'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 
                            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 
                            'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 
                            'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 
                            'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 
                            'through', 'during', 'before', 'after', 'above', 'below', 'to', 
                            'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 
                            'again', 'further', 'then', 'once', 'here', 'there', 'when', 
                            'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 
                            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 
                            'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 
                            'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 
                            're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 
                            'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', 
                            "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', 
                            "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', 
                            "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', 
                            "weren't", 'won', "won't", 'wouldn', "wouldn't"])
        
        # Calculate word frequencies
        word_frequencies = FreqDist()
        for sentence in sentences:
            for word in nltk.word_tokenize(sentence.lower()):
                if word not in stop_words and word.isalnum():
                    word_frequencies[word] += 1
        
        # Normalize word frequencies
        if word_frequencies:
            max_frequency = max(word_frequencies.values())
            for word in word_frequencies:
                word_frequencies[word] = word_frequencies[word] / max_frequency
        
        # Calculate sentence scores
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            for word in nltk.word_tokenize(sentence.lower()):
                if word in word_frequencies:
                    if i not in sentence_scores:
                        sentence_scores[i] = word_frequencies[word]
                    else:
                        sentence_scores[i] += word_frequencies[word]
        
        # Get the top sentences
        summary_sentences_indices = nlargest(num_sentences, sentence_scores, key=sentence_scores.get)
        summary_sentences_indices = sorted(summary_sentences_indices)
        
        # Create the summary
        summary = ' '.join([sentences[i] for i in summary_sentences_indices])
        
        return summary
    
    except Exception as e:
        logger.error(f"Error generating extractive summary: {str(e)}")
        return "Unable to generate summary."
        
def generate_journalist_summary(text, num_sentences=4):
    """
    Generate a journalist-style summary with better flow and readability
    
    Args:
        text: The text to summarize
        num_sentences: Base number of sentences to include (may be adjusted)
        
    Returns:
        A journalist-style summary with improved readability
    """
    try:
        # First get the extractive summary as a base
        base_summary = generate_extractive_summary(text, num_sentences)
        sentences = sent_tokenize(base_summary)
        
        # Simple improvements to make the summary more journalistic
        
        # 1. Remove redundant information and connect sentences better
        if len(sentences) > 1:
            # Track entities to avoid repetition
            entities = set()
            improved_sentences = []
            
            for i, sentence in enumerate(sentences):
                # Simple entity extraction (people, organizations) - just a heuristic
                words = nltk.word_tokenize(sentence)
                sentence_entities = [word for word in words if word[0].isupper() and len(word) > 1]
                
                # Remove sentences with too many repeated entities
                overlap = sum(1 for entity in sentence_entities if entity in entities)
                if i == 0 or overlap < len(sentence_entities) / 2:
                    improved_sentences.append(sentence)
                    entities.update(sentence_entities)
            
            # If we filtered too many sentences, add back some original ones
            if len(improved_sentences) < max(2, num_sentences // 2):
                improved_sentences = sentences[:max(2, num_sentences // 2)]
            
            # Improve lead-in for the second sentence if it exists
            if len(improved_sentences) > 1:
                second = improved_sentences[1]
                
                # If the second sentence starts with a person/entity, add a transition
                words = nltk.word_tokenize(second)
                if words and words[0][0].isupper() and not second.startswith("The "):
                    # Add a journalistic transition
                    connectors = ["Additionally, ", "Furthermore, ", "According to experts, ", 
                                 "Sources indicate ", "Officials say ", "Reports suggest ", 
                                 "Analysts note ", "The report indicates ", "Importantly, "]
                    
                    import random
                    connector = random.choice(connectors)
                    improved_sentences[1] = connector + second[0].lower() + second[1:]
            
            # Join the improved sentences
            summary = ' '.join(improved_sentences)
        else:
            summary = base_summary
        
        # 2. Add a stronger journalistic opening if possible
        sentences = sent_tokenize(summary)
        if sentences:
            # Try to identify key facts for a stronger opening
            first_sentence = sentences[0]
            words = nltk.word_tokenize(first_sentence.lower())
            
            # Check if it already has a strong journalistic opening
            has_strong_opening = any(word in words for word in ['breaking', 'exclusive', 'just', 'today', 'reveals', 'announced'])
            
            if not has_strong_opening and len(sentences) > 1:
                # Extract key entities from the text for potential lead-in
                all_words = nltk.word_tokenize(text.lower())
                freq_dist = FreqDist(all_words)
                common_words = [word for word, freq in freq_dist.most_common(10) 
                               if word.isalnum() and len(word) > 3]
                
                if common_words:
                    key_term = common_words[0].title()
                    # Create a more engaging opening
                    strong_openings = [
                        f"In a significant development, {first_sentence.lower()}",
                        f"A new report on {key_term} reveals that {first_sentence.lower()}",
                        f"Analysis shows {first_sentence.lower()}",
                        f"Recent developments indicate {first_sentence.lower()}"
                    ]
                    
                    import random
                    sentences[0] = random.choice(strong_openings)
                    summary = ' '.join(sentences)
        
        return summary
    
    except Exception as e:
        logger.error(f"Error generating journalist summary: {str(e)}")
        # Fall back to standard summary
        return generate_extractive_summary(text, num_sentences)

def generate_twitter_summary(text, max_length=200):
    """
    Generate a Twitter-friendly summary optimized for sharing
    
    Args:
        text: The text to summarize
        max_length: Maximum character length (default: 200, leaves room for URL)
        
    Returns:
        A concise summary suitable for sharing on Twitter/X
    """
    try:
        # Get a very short extractive summary as a base
        base_summary = generate_extractive_summary(text, num_sentences=2)
        
        # Simplify and shorten for Twitter
        sentences = sent_tokenize(base_summary)
        
        if not sentences:
            return "New executive order issued. Click to learn more."
        
        # Take just the first sentence for Twitter and trim if needed
        twitter_text = sentences[0]
        
        # If we have an executive order, try to extract just the main action
        if "executive order" in text.lower():
            # Look for action verbs and policy details
            action_phrases = [
                "requires", "mandates", "establishes", "creates", "revokes",
                "amends", "modifies", "directs", "prohibits", "restricts",
                "allows", "permits", "authorizes", "expands", "reduces"
            ]
            
            sentences = sent_tokenize(text)
            for sentence in sentences:
                if any(phrase in sentence.lower() for phrase in action_phrases):
                    twitter_text = sentence
                    break
        
        # If it's still too long, truncate intelligently
        if len(twitter_text) > max_length:
            # Try to find a good breaking point
            words = twitter_text.split()
            truncated_text = ""
            for word in words:
                if len(truncated_text + " " + word) + 3 <= max_length: # +3 for "..."
                    truncated_text += " " + word if truncated_text else word
                else:
                    break
            
            twitter_text = truncated_text + "..."
        
        # Add a call to action
        if "executive order" in text.lower():
            twitter_text = "BREAKING: New Executive Order: " + twitter_text
            
        # Add hashtags if space permits
        if "executive order" in text.lower() and len(twitter_text) + 12 <= max_length:
            twitter_text += " #ExecutiveOrder"
            
        return twitter_text
    
    except Exception as e:
        logger.error(f"Error generating Twitter summary: {str(e)}")
        # Provide a generic fallback
        return "New executive order issued by the White House. Click to read the details."
