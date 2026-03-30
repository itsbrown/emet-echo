import os
import logging
import requests
import re
import html
import json
from datetime import datetime
from app import db
from models import ExecutiveOrder
from summarizer import generate_summary
from html_utils import extract_plain_text

try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception:
    _openai_client = None

# Set up logging
logger = logging.getLogger(__name__)

# Mock data for initial setup - these will be replaced with real executive orders once Trump's term starts
SAMPLE_EXECUTIVE_ORDERS = [
    {
        "order_number": "EO-2025-001",
        "title": "Executive Order on Protecting Americans Against Foreign Terrorism",
        "date_issued": "2025-01-20",
        "full_text": "By the authority vested in me as President by the Constitution and the laws of the United States of America, including the Immigration and Nationality Act (INA), 8 U.S.C. 1101 et seq., and section 301 of title 3, United States Code, and to protect the American people from terrorist attacks by foreign nationals admitted to the United States, it is hereby ordered as follows:\n\nSection 1. Purpose. The visa-issuance process plays a crucial role in detecting individuals with terrorist ties and stopping them from entering the United States. Perhaps in no instance was that more apparent than the terrorist attacks of September 11, 2001, when State Department policy prevented consular officers from properly scrutinizing the visa applications of several of the 19 foreign nationals who went on to murder nearly 3,000 Americans. And while the visa-issuance process was reviewed and amended after the September 11 attacks to better detect would-be terrorists from receiving visas, these measures did not stop attacks by foreign nationals who were admitted to the United States.\n\nNumerous foreign-born individuals have been convicted or implicated in terrorism-related crimes since September 11, 2001, including foreign nationals who entered the United States after receiving visitor, student, or employment visas, or who entered through the United States refugee resettlement program. Deteriorating conditions in certain countries due to war, strife, disaster, and civil unrest increase the likelihood that terrorists will use any means possible to enter the United States. The United States must be vigilant during the visa-issuance process to ensure that those approved for admission do not intend to harm Americans and that they have no ties to terrorism.",
        "summary": "This executive order focuses on strengthening the visa issuance process to prevent potential terrorists from entering the United States. It references the September 11 attacks as evidence of past failures in the screening system and notes that foreign nationals have been involved in terrorism since then. The order calls for increased vigilance in the visa process, particularly for countries experiencing war, strife, disaster, or civil unrest.",
        "status": "Pending Implementation",
        "category": "Immigration, National Security",
        "url": "https://www.whitehouse.gov/presidential-actions/executive-order-protecting-nation-foreign-terrorist-entry-united-states/",
        "source": "White House"
    },
    {
        "order_number": "EO-2025-002",
        "title": "Executive Order on America-First Energy Policy",
        "date_issued": "2025-01-22",
        "full_text": "By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered as follows:\n\nSection 1. Policy. It is in the national interest to promote clean and safe development of our Nation's vast energy resources, while at the same time avoiding regulatory burdens that unnecessarily encumber energy production, constrain economic growth, and prevent job creation. Moreover, the prudent development of these natural resources is essential to ensuring the Nation's geopolitical security.\n\nSection 2. Immediate Review of All Agency Actions that Potentially Burden the Safe, Efficient Development of Domestic Energy Resources. (a) The heads of all agencies shall review all existing regulations, orders, guidance documents, policies, and any other similar agency actions that potentially burden the development or use of domestically produced energy resources, with particular attention to oil, natural gas, coal, and nuclear energy resources. Such review shall not include agency actions that are mandated by law, necessary for the public interest, and consistent with the policy set forth in section 1 of this order.\n\nSection 3. Lifting the Moratorium on Federal Coal Leasing. The Secretary of the Interior shall take all steps necessary and appropriate to amend or withdraw the Federal Land Coal Leasing Moratorium, and all activities associated with its implementation, thereby lifting the moratorium on federal coal leasing activities.",
        "summary": "This executive order establishes an America-First energy policy focused on developing domestic energy resources while reducing regulatory burdens. It requires agencies to review regulations that could hinder domestic energy production, particularly for oil, natural gas, coal, and nuclear energy. The order specifically lifts the moratorium on federal coal leasing to promote coal industry growth.",
        "status": "Pending Implementation",
        "category": "Energy, Environment",
        "url": "https://www.whitehouse.gov/presidential-actions/executive-order-promoting-energy-independence-economic-growth/",
        "source": "White House"
    },
    {
        "order_number": "EO-2025-003",
        "title": "Executive Order on Reducing Regulation and Controlling Regulatory Costs",
        "date_issued": "2025-01-25",
        "full_text": "By the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered as follows:\n\nSection 1. Purpose. It is the policy of the executive branch to be prudent and financially responsible in the expenditure of funds, from both public and private sources. In addition to the management of the direct expenditure of taxpayer dollars through the budgeting process, it is essential to manage the costs associated with the governmental imposition of private expenditures required to comply with Federal regulations. Toward that end, it is important that for every one new regulation issued, at least two prior regulations be identified for elimination, and that the cost of planned regulations be prudently managed and controlled through a budgeting process.\n\nSection 2. Regulatory Cap for Fiscal Year 2025. (a) Unless prohibited by law, whenever an executive department or agency publicly proposes for notice and comment or otherwise promulgates a new regulation, it shall identify at least two existing regulations to be repealed.\n\nSection 3. Annual Regulatory Cost Submissions to the Office of Management and Budget. (a) Beginning with fiscal year 2025, during the Presidential budget process, the Director of the Office of Management and Budget shall identify to agencies a total amount of incremental costs that will be allowed for each agency in issuing new regulations and repealing regulations for the next fiscal year. No regulations exceeding the agency's total incremental cost allowance will be permitted in that fiscal year, unless required by law or approved in writing by the Director.",
        "summary": "This executive order aims to reduce regulations and control regulatory costs by implementing a 'two-for-one' rule requiring agencies to eliminate two existing regulations for each new one created. It establishes a regulatory budget process where the Office of Management and Budget will set annual limits on the incremental costs agencies can impose through regulations. This approach seeks to reduce the financial burden of government regulations on businesses and individuals.",
        "status": "Pending Implementation",
        "category": "Government Efficiency, Economy",
        "url": "https://www.whitehouse.gov/presidential-actions/executive-order-reducing-regulation-controlling-regulatory-costs/",
        "source": "White House"
    }
]

def fetch_executive_orders(since_date=None):
    """
    Fetch executive orders from the Federal Register API via pagination.
    Fetches all executive orders signed since January 20, 2025 (or since
    since_date if provided for incremental updates).

    Args:
        since_date: Optional datetime; only fetch orders signed after this date.
                    If None, fetches all orders from January 20, 2025 onward.

    Returns:
        List of executive order dictionaries
    """
    try:
        base_url = "https://www.federalregister.gov/api/v1/documents"

        start_date = since_date.strftime('%Y-%m-%d') if since_date else "2025-01-20"

        fields = [
            "citation", "document_number", "end_page", "html_url",
            "body_html_url", "pdf_url", "publication_date",
            "signing_date", "start_page", "title", "raw_text_url",
            "disposition_notes", "executive_order_number"
        ]

        all_results = []
        page = 1

        while True:
            params = {
                "conditions[presidential_document_type_id]": 2,
                "conditions[type]": "PRESDOCU",
                "conditions[signing_date][gte]": start_date,
                "order": "newest",
                "per_page": 100,
                "page": page,
                "fields[]": fields
            }

            logger.info(f"Fetching executive orders page {page} from Federal Register API (since {start_date})")
            response = requests.get(base_url, params=params, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to fetch executive orders page {page}: Status code {response.status_code}")
                break

            data = response.json()
            results = data.get("results", [])
            all_results.extend(results)

            total_pages = data.get("total_pages", 1)
            logger.info(f"Fetched page {page}/{total_pages} — {len(results)} orders on this page")

            if page >= total_pages:
                break

            page += 1

        logger.info(f"Total executive orders fetched from API: {len(all_results)}")

        if not all_results:
            logger.info("API returned zero executive orders for the given date range — nothing to import")
            return []

        executive_orders = []
        for order in all_results:
            full_text = ""
            if "raw_text_url" in order and order["raw_text_url"]:
                try:
                    text_response = requests.get(order["raw_text_url"], timeout=30)
                    if text_response.status_code == 200:
                        raw_text = text_response.text
                        if raw_text:
                            full_text = raw_text.replace('\x00', '')
                            full_text = full_text.replace('\r\n', '\n').replace('\r', '\n')
                            full_text = ''.join(c if ord(c) >= 32 or c in '\n\t' else ' ' for c in full_text)
                            full_text = extract_plain_text(full_text)
                except Exception as e:
                    logger.error(f"Error fetching full text: {str(e)}")

            date_str = order.get("signing_date") or order.get("publication_date", "")

            eo_number = order.get("executive_order_number", "")
            if not eo_number and "document_number" in order:
                eo_number = order["document_number"]

            executive_order = {
                "order_number": f"EO-{eo_number}",
                "title": order.get("title", "Executive Order"),
                "date_issued": date_str,
                "full_text": full_text,
                "summary": "",
                "status": "Active",
                "category": "Federal Regulation",
                "url": order.get("html_url", ""),
                "source": "Federal Register"
            }

            executive_orders.append(executive_order)

        return executive_orders

    except Exception as e:
        logger.error(f"Error fetching executive orders: {str(e)}")
        return []

def summarize_order(order_text, style="journalist"):
    """
    Generate AI summary of executive order text using our summarizer
    
    Args:
        order_text: Full text of the executive order
        style: Summary style - "standard", "journalist", or "twitter" (default: "journalist")
        
    Returns:
        A summary of the executive order in the specified style
    """
    try:
        # Import HTML cleaning and summary generation functions
        from summarizer import generate_summary, clean_html
        
        # First clean any HTML from the input text
        cleaned_text = clean_html(order_text)
        
        # Generate the summary using our enhanced summarizer
        summary = generate_summary(cleaned_text, num_sentences=5, style=style)
        
        # Double-check that the summary doesn't contain any HTML
        import re
        import html
        
        # Unescape HTML entities
        summary = html.unescape(summary)
        
        # Remove any HTML tags that may remain
        summary = re.sub(r'<[^>]*>', ' ', summary)
        
        # Remove residual Federal Register formatting that might remain
        summary = re.sub(r'Federal Register.*?\n', '', summary)
        summary = re.sub(r'Presidential Documents.*?\n', '', summary)
        summary = re.sub(r'FR Doc.*?\n', '', summary)
        summary = re.sub(r'Volume \d+.*?\n', '', summary)
        summary = re.sub(r'Pages \d+-\d+.*?\n', '', summary)
        
        # Fix spacing issues
        summary = re.sub(r'\s+', ' ', summary).strip()
        
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        # Return a clean portion of the text as fallback
        import html
        import re
        # Clean the fallback text as well
        fallback = html.unescape(order_text[:300])
        fallback = re.sub(r'<[^>]*>', ' ', fallback)
        fallback = re.sub(r'\s+', ' ', fallback).strip()
        return fallback + "..."

def generate_twitter_summary_for_order(order_text):
    """
    Generate a Twitter/X-friendly summary for an executive order
    
    Args:
        order_text: Full text of the executive order
        
    Returns:
        A concise summary suitable for sharing on Twitter/X
    """
    try:
        # First clean the input text
        from summarizer import clean_html
        cleaned_text = clean_html(order_text)
        
        # Use our specialized Twitter summary generator
        summary = generate_summary(cleaned_text, style="twitter")
        
        # Clean the summary text again to be extra sure it has no HTML content
        summary = clean_html(summary)
        
        # Add cleanup to remove Federal Register-specific formatting that might remain
        summary = re.sub(r'Federal Register|Presidential Documents|FR Doc|Pages \d+-\d+', '', summary)
        
        # Normalize whitespace
        summary = ' '.join(summary.split())
        
        return summary
    except Exception as e:
        logger.error(f"Error generating Twitter summary: {str(e)}")
        # Provide a generic fallback
        return "New executive order issued by the White House. Click to read the details."

def initialize_executive_orders(force_refresh=False):
    """
    Initialize or incrementally update the database with executive orders.

    On an empty database (or when force_refresh=True after clearing), fetches all
    executive orders from January 20, 2025 onward via paginated API calls.

    On subsequent runs, only fetches orders newer than the most recent one already
    stored — no unnecessary deletes or re-fetches.

    Args:
        force_refresh: If True, delete all existing records and re-fetch everything.
    """
    try:
        existing_count = ExecutiveOrder.query.count()

        if force_refresh and existing_count > 0:
            logger.info(f"force_refresh=True: deleting {existing_count} existing executive orders")
            ExecutiveOrder.query.delete()
            db.session.commit()
            existing_count = 0

        # Determine the since_date for incremental updates
        since_date = None
        if existing_count > 0:
            latest_order = ExecutiveOrder.query.order_by(ExecutiveOrder.date_issued.desc()).first()
            if latest_order and latest_order.date_issued:
                # Advance by one day so we only fetch strictly newer orders
                from datetime import timedelta as _td
                since_date = latest_order.date_issued + _td(days=1)
                logger.info(f"Incremental update: fetching orders newer than {latest_order.date_issued.date()} (since {since_date.date()})")
            else:
                logger.info("No dated orders found; fetching full dataset from 2025-01-20")
        else:
            logger.info("Empty database: fetching all executive orders from 2025-01-20")

        # Fetch executive orders from Federal Register API
        orders = fetch_executive_orders(since_date=since_date)
        logger.info(f"Fetched {len(orders)} executive orders from Federal Register API")
        
        # Process and store each order
        for order_data in orders:
            # Check if order already exists
            existing = ExecutiveOrder.query.filter_by(order_number=order_data['order_number']).first()
            if existing:
                logger.info(f"Executive order {order_data['order_number']} already exists, skipping")
                continue
            
            # Create new executive order
            try:
                # Parse date with flexible format handling
                date_issued = None
                if order_data['date_issued']:
                    date_str = order_data['date_issued']
                    try:
                        # Try ISO format (YYYY-MM-DD)
                        date_issued = datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        try:
                            # Try Federal Register format (YYYY-MM-DD)
                            date_issued = datetime.strptime(date_str, '%Y-%m-%d')
                        except ValueError:
                            try:
                                # Try another common format (MM/DD/YYYY)
                                date_issued = datetime.strptime(date_str, '%m/%d/%Y')
                            except ValueError:
                                # Default to current date if all parsing attempts fail
                                logger.warning(f"Could not parse date '{date_str}', using current date")
                                date_issued = datetime.now()
                else:
                    # If no date provided, use current date
                    date_issued = datetime.now()
                
                # Generate summary if not provided
                summary = order_data.get('summary', '')
                if not summary and order_data['full_text']:
                    summary = summarize_order(order_data['full_text'])
                
                # Create new order
                new_order = ExecutiveOrder(
                    order_number=order_data['order_number'],
                    title=order_data['title'],
                    date_issued=date_issued,
                    full_text=order_data['full_text'],
                    summary=summary,
                    status=order_data.get('status', 'Active'),
                    category=order_data.get('category', 'Federal Regulation'),
                    url=order_data.get('url', ''),
                    source=order_data.get('source', 'Federal Register')
                )
                
                # Add to database
                db.session.add(new_order)
                logger.info(f"Added executive order {order_data['order_number']}")
            except Exception as e:
                logger.error(f"Error adding executive order {order_data.get('order_number')}: {str(e)}")
                logger.error(f"Exception details: {e}")
        
        # Commit all changes
        db.session.commit()
        logger.info("Executive orders initialized successfully")
    
    except Exception as e:
        logger.error(f"Error initializing executive orders: {str(e)}")
        db.session.rollback()


def generate_ai_quip(order):
    """
    Generate a punchy one-liner AI quip for an executive order.
    ≤20 words, opinionated but fair, em-dash style.
    Stores the result in order.ai_quip and commits to the database.
    """
    if not _openai_client:
        logger.warning("OpenAI client not available — skipping ai_quip generation")
        return

    source_text = order.ai_summary or order.summary or order.title or ""
    source_text = source_text[:1500]

    prompt = f"""You are a sharp, independent political analyst. Write exactly ONE punchy sentence (≤20 words) summarising this executive order from an independent perspective. Use an em-dash (—) to split cause and consequence. Be opinionated but fair. Example style: "Cuts EPA drilling rules — energy prices may fall, but loopholes concern watchdogs."

Executive Order: {order.order_number}
Title: {order.title}
Summary: {source_text}

Return only the single sentence, no quotes, no punctuation other than the em-dash and a period at the end."""

    try:
        response = _openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.7
        )
        quip = response.choices[0].message.content.strip().strip('"').strip("'")
        order.ai_quip = quip
        db.session.commit()
        logger.info(f"ai_quip generated for {order.order_number}: {quip}")
    except Exception as e:
        logger.error(f"Error generating ai_quip for {order.order_number}: {e}")

# ---------------------------------------------------------------------------
# America First economic & crime context helpers
# ---------------------------------------------------------------------------

AMERICA_FIRST_SMALL_BIZ_PROMPT = """
You are an America First analyst focused on small business success and Main Street America.

For every Executive Order, news story, or policy, evaluate it strictly against these core metrics of what makes America Great:
- Lower unemployment and higher real wages for American workers
- Increased small business formation, survival, and growth rates (Census BFS)
- Higher domestic production and GDP contribution from small firms and manufacturers
- Reduced regulatory burden and compliance costs on small businesses
- LOWER CRIME RATES (FBI UCR/NIBRS data), especially violent crime and property crime in communities where small businesses operate — safer streets mean more foot traffic, lower insurance costs, and better employee retention for Main Street
- Increased low-income home ownership and economic mobility for working families

Prioritize the small-business angle: How does this policy help or hurt Main Street entrepreneurs, mom-and-pop shops, family farms, independent contractors, and small manufacturers?
Highlight wins for deregulation, energy independence, fair trade, tax relief, reduced bureaucracy, or stronger law enforcement that protects businesses.
Note risks (e.g., higher costs or crime spikes that hurt retail/restaurants).

Use recent FBI crime data (violent crime rate, property crime rate, trends from Crime Data Explorer) alongside BLS unemployment/wages and Census BFS business formations.
Frame everything through the lens of putting American workers, families, and small businesses first. Use factual, optimistic language when data supports positive outcomes.
Keep tone straightforward and pro-America — never neutral "both sides" language.
"""

_econ_cache = {}


def _econ_cache_key():
    return datetime.now().strftime("%Y%m%d")


def _get_cached_econ_context():
    key = _econ_cache_key()
    if _econ_cache.get("_key") == key and "data" in _econ_cache:
        return _econ_cache["data"]
    data = get_economic_crime_context()
    _econ_cache["_key"] = key
    _econ_cache["data"] = data
    return data


def get_bls_unemployment():
    try:
        headers = {'Content-type': 'application/json'}
        data = json.dumps({
            "seriesid": ["LNS14000000"],
            "startyear": str(datetime.now().year - 1),
            "endyear": str(datetime.now().year)
        })
        response = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=data, headers=headers, timeout=10)
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get('status') == 'REQUEST_SUCCEEDED':
                latest = json_data['Results']['series'][0]['data'][0]
                return {"unemployment_rate": float(latest['value']), "period": f"{latest['year']}-{latest['period']}"}
    except Exception as e:
        logger.error(f"BLS fetch error: {e}")
    return {"error": "unavailable"}


def get_fbi_crime_data():
    try:
        url = "https://api.usa.gov/crime/fbi/sapi/api/summarized/estimates/national"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "violent_crime_rate": data.get("violent_crime_rate_per_100k", "N/A"),
                "property_crime_rate": data.get("property_crime_rate_per_100k", "N/A"),
                "note": "Lower crime supports safer business districts, lower insurance, more customer traffic"
            }
    except Exception as e:
        logger.error(f"FBI crime fetch error: {e}")
    return {"error": "unavailable"}


def get_economic_crime_context():
    return {
        "bls": get_bls_unemployment(),
        "fbi_crime": get_fbi_crime_data(),
        "census_bfs": {"note": "Small business formation trends from Census Bureau BFS"}
    }


def generate_ai_analysis(order):
    """
    Generate AI analysis for an executive order using OpenAI.
    Populates ai_summary, indie_vs_mainstream (stores small_business_impact), historical_context, data_ties fields.
    Stores results in the database (called once per order, cached thereafter).

    Args:
        order: ExecutiveOrder model instance
    """
    if not _openai_client:
        logger.warning("OpenAI client not available — skipping AI analysis")
        return

    source_text = order.full_text or order.summary or order.title or ""
    source_text = source_text[:6000]

    context_dict = _get_cached_econ_context()

    user_message = (
        f"Analyze this Executive Order from an America First small business perspective. "
        f"Include relevant FBI crime trends if applicable:\n\n{source_text}\n\n"
        f"Context data: {json.dumps(context_dict)}\n\n"
        f"Return a JSON object with exactly these four keys:\n"
        f'1. "ai_summary": A 150-250 word America First summary focused on small business impact.\n'
        f'2. "small_business_impact": A JSON object with two keys: '
        f'"wins" (2-3 sentences on how this EO helps Main Street small businesses, deregulation, or lower crime) '
        f'and "risks" (2-3 sentences on potential cost increases, regulatory burdens, or other risks for small businesses).\n'
        f'3. "historical_context": 3-4 bullet points (plain text, each starting with "•") connecting this EO to historical precedents '
        f'— mention specific prior administrations and EO issuance waves when relevant.\n'
        f'4. "data_ties": 2-3 sentences on relevant economic or social data context (BLS unemployment, wages, FBI crime rates, Census BFS) '
        f'that relate to the stated goals of this EO.\n\n'
        f"Return only valid JSON, no markdown fences."
    )

    try:
        response = _openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": AMERICA_FIRST_SMALL_BIZ_PROMPT},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1200,
            temperature=0.5
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        data = json.loads(raw)

        order.ai_summary = data.get("ai_summary", "")
        small_biz = data.get("small_business_impact", {})
        if isinstance(small_biz, dict):
            order.indie_vs_mainstream = json.dumps(small_biz)
        else:
            order.indie_vs_mainstream = json.dumps({"wins": str(small_biz), "risks": ""})
        order.historical_context = data.get("historical_context", "")
        order.data_ties = data.get("data_ties", "")

        db.session.commit()
        logger.info(f"AI analysis generated and cached for {order.order_number}")

        # Also generate the ai_quip if not already set
        if not order.ai_quip:
            try:
                generate_ai_quip(order)
            except Exception as _qe:
                logger.warning(f"ai_quip generation failed after analysis for {order.order_number}: {_qe}")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI JSON response for {order.order_number}: {e}")
    except Exception as e:
        logger.error(f"Error generating AI analysis for {order.order_number}: {e}")