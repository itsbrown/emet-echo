import nltk
import ssl
import logging
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from heapq import nlargest

# Set up logging
logger = logging.getLogger(__name__)

# Download NLTK resources - handle SSL issues gracefully
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    try:
        # Try with SSL context
        try:
            _create_unverified_https_context = ssl._create_unverified_context
        except AttributeError:
            pass
        else:
            ssl._create_default_https_context = _create_unverified_https_context
        
        nltk.download('punkt')
    except Exception as e:
        logger.error(f"Failed to download NLTK punkt: {str(e)}")

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    try:
        nltk.download('stopwords')
    except Exception as e:
        logger.error(f"Failed to download NLTK stopwords: {str(e)}")

def generate_summary(text, num_sentences=3):
    """
    Generate a summary of the given text using extractive summarization
    
    Args:
        text: The text to summarize
        num_sentences: Number of sentences in the summary (default: 3)
        
    Returns:
        A summary of the text
    """
    if not text or text == "Content not available":
        return "Summary not available."
    
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
        logger.error(f"Error generating summary: {str(e)}")
        return "Unable to generate summary."
