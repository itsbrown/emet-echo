import os
import logging
import requests
from datetime import datetime, timedelta
from functools import wraps
import time
import json

logger = logging.getLogger(__name__)

PRINTIFY_API_TOKEN = os.environ.get("PRINTIFY_API_TOKEN")
PRINTIFY_BASE_URL = "https://api.printify.com/v1"
SHOP_URL = "https://shop.emetecho.com"

_cache = {
    "shop_id": None,
    "shop_id_fetched_at": None,
    "products": [],
    "products_fetched_at": None
}

CACHE_DURATION = timedelta(minutes=30)

def _get_headers():
    if not PRINTIFY_API_TOKEN:
        return None
    return {
        "Authorization": f"Bearer {PRINTIFY_API_TOKEN}",
        "User-Agent": "EmetEcho/1.0 Flask",
        "Content-Type": "application/json"
    }

def _rate_limit_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                return result
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited by Printify API. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise
        return None
    return wrapper

@_rate_limit_handler
def get_shop_id():
    global _cache
    
    if _cache["shop_id"] and _cache["shop_id_fetched_at"]:
        if datetime.now() - _cache["shop_id_fetched_at"] < CACHE_DURATION:
            return _cache["shop_id"]
    
    headers = _get_headers()
    if not headers:
        logger.error("PRINTIFY_API_TOKEN not set")
        return None
    
    try:
        response = requests.get(
            f"{PRINTIFY_BASE_URL}/shops.json",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        
        shops = response.json()
        if shops and len(shops) > 0:
            _cache["shop_id"] = shops[0]["id"]
            _cache["shop_id_fetched_at"] = datetime.now()
            logger.info(f"Retrieved shop ID: {_cache['shop_id']}")
            return _cache["shop_id"]
        
        logger.warning("No shops found in Printify account")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching shop ID: {str(e)}")
        return None

@_rate_limit_handler
def fetch_products(limit=50):
    global _cache
    
    if _cache["products"] and _cache["products_fetched_at"]:
        if datetime.now() - _cache["products_fetched_at"] < CACHE_DURATION:
            logger.info(f"Returning {len(_cache['products'])} cached products")
            return _cache["products"]
    
    shop_id = get_shop_id()
    if not shop_id:
        logger.error("Cannot fetch products without shop ID")
        return []
    
    headers = _get_headers()
    if not headers:
        logger.error("PRINTIFY_API_TOKEN not set")
        return []
    
    try:
        response = requests.get(
            f"{PRINTIFY_BASE_URL}/shops/{shop_id}/products.json",
            headers=headers,
            params={"limit": limit},
            timeout=15
        )
        response.raise_for_status()
        
        data = response.json()
        products = data.get("data", [])
        
        processed_products = []
        for product in products:
            processed = process_product(product)
            if processed:
                processed_products.append(processed)
        
        _cache["products"] = processed_products
        _cache["products_fetched_at"] = datetime.now()
        
        logger.info(f"Fetched and processed {len(processed_products)} products from Printify")
        return processed_products
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching products: {str(e)}")
        return _cache.get("products", [])

def process_product(product):
    try:
        product_id = product.get("id", "")
        title = product.get("title", "Untitled Product")
        description = product.get("description", "")
        
        images = product.get("images", [])
        primary_image = None
        for img in images:
            if img.get("is_default"):
                primary_image = img.get("src")
                break
        if not primary_image and images:
            primary_image = images[0].get("src")
        
        variants = product.get("variants", [])
        prices = [v.get("price", 0) for v in variants if v.get("price")]
        min_price = min(prices) / 100 if prices else 0
        max_price = max(prices) / 100 if prices else 0
        
        tags = product.get("tags", [])
        
        is_visible = product.get("visible", True)
        
        return {
            "id": product_id,
            "title": title,
            "description": description,
            "image_url": primary_image,
            "min_price": min_price,
            "max_price": max_price,
            "price_display": f"${min_price:.2f}" if min_price == max_price else f"${min_price:.2f} - ${max_price:.2f}",
            "tags": tags,
            "is_visible": is_visible,
            "shop_url": SHOP_URL,
            "product_url": f"{SHOP_URL}/products/{product_id}"
        }
    except Exception as e:
        logger.error(f"Error processing product: {str(e)}")
        return None

def get_featured_products(count=6):
    products = fetch_products()
    visible_products = [p for p in products if p.get("is_visible", True)]
    return visible_products[:count]

def get_products_by_tag(tag, count=6):
    products = fetch_products()
    matching = [p for p in products if tag.lower() in [t.lower() for t in p.get("tags", [])]]
    return matching[:count]

def clear_cache():
    global _cache
    _cache = {
        "shop_id": None,
        "shop_id_fetched_at": None,
        "products": [],
        "products_fetched_at": None
    }
    logger.info("Printify cache cleared")

def save_products_to_db(db_session, PrintifyProduct):
    products = fetch_products()
    
    saved_count = 0
    for product in products:
        try:
            existing = PrintifyProduct.query.filter_by(printify_id=product["id"]).first()
            
            if existing:
                existing.title = product["title"]
                existing.description = product["description"]
                existing.image_url = product["image_url"]
                existing.min_price = product["min_price"]
                existing.max_price = product["max_price"]
                existing.tags = json.dumps(product["tags"])
                existing.is_visible = product["is_visible"]
                existing.updated_at = datetime.utcnow()
            else:
                new_product = PrintifyProduct(
                    printify_id=product["id"],
                    title=product["title"],
                    description=product["description"],
                    image_url=product["image_url"],
                    min_price=product["min_price"],
                    max_price=product["max_price"],
                    tags=json.dumps(product["tags"]),
                    is_visible=product["is_visible"]
                )
                db_session.add(new_product)
            
            saved_count += 1
        except Exception as e:
            logger.error(f"Error saving product {product.get('id')}: {str(e)}")
            continue
    
    try:
        db_session.commit()
        logger.info(f"Saved {saved_count} products to database")
    except Exception as e:
        logger.error(f"Error committing products to database: {str(e)}")
        db_session.rollback()
    
    return saved_count

def get_products_from_db(PrintifyProduct, count=6):
    try:
        products = PrintifyProduct.query.filter_by(is_visible=True).limit(count).all()
        return [{
            "id": p.printify_id,
            "title": p.title,
            "description": p.description,
            "image_url": p.image_url,
            "min_price": p.min_price,
            "max_price": p.max_price,
            "price_display": f"${p.min_price:.2f}" if p.min_price == p.max_price else f"${p.min_price:.2f} - ${p.max_price:.2f}",
            "tags": json.loads(p.tags) if p.tags else [],
            "is_visible": p.is_visible,
            "shop_url": SHOP_URL,
            "product_url": f"{SHOP_URL}/products/{p.printify_id}"
        } for p in products]
    except Exception as e:
        logger.error(f"Error fetching products from database: {str(e)}")
        return []
