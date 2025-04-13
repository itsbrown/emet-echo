import os
import logging
import requests
from datetime import datetime
from app import db
from models import ExecutiveOrder
from summarizer import generate_summary

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

def fetch_executive_orders():
    """
    Fetch Trump executive orders from official sources
    This will be replaced with real API calls once Trump's term begins
    """
    return SAMPLE_EXECUTIVE_ORDERS

def summarize_order(order_text):
    """
    Generate AI summary of executive order text using our summarizer
    
    Args:
        order_text: Full text of the executive order
        
    Returns:
        A summary of the executive order
    """
    try:
        # Generate summary using our existing summarizer
        summary = generate_summary(order_text, num_sentences=5)
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        # Return a portion of the text as fallback
        return order_text[:300] + "..."

def initialize_executive_orders():
    """
    Initialize the database with executive orders
    """
    try:
        # Check if we already have orders in the database
        existing_count = ExecutiveOrder.query.count()
        if existing_count > 0:
            logger.info(f"Found {existing_count} executive orders in database, skipping initialization")
            return
        
        # Fetch executive orders
        orders = fetch_executive_orders()
        logger.info(f"Fetched {len(orders)} executive orders")
        
        # Process and store each order
        for order_data in orders:
            # Check if order already exists
            existing = ExecutiveOrder.query.filter_by(order_number=order_data['order_number']).first()
            if existing:
                logger.info(f"Executive order {order_data['order_number']} already exists, skipping")
                continue
            
            # Create new executive order
            try:
                # Parse date
                date_issued = datetime.strptime(order_data['date_issued'], '%Y-%m-%d')
                
                # Create new order
                new_order = ExecutiveOrder(
                    order_number=order_data['order_number'],
                    title=order_data['title'],
                    date_issued=date_issued,
                    full_text=order_data['full_text'],
                    summary=order_data.get('summary') or summarize_order(order_data['full_text']),
                    status=order_data.get('status', 'Active'),
                    category=order_data.get('category', ''),
                    url=order_data.get('url', ''),
                    source=order_data.get('source', '')
                )
                
                # Add to database
                db.session.add(new_order)
                logger.info(f"Added executive order {order_data['order_number']}")
            except Exception as e:
                logger.error(f"Error adding executive order {order_data.get('order_number')}: {str(e)}")
        
        # Commit all changes
        db.session.commit()
        logger.info("Executive orders initialized successfully")
    
    except Exception as e:
        logger.error(f"Error initializing executive orders: {str(e)}")
        db.session.rollback()