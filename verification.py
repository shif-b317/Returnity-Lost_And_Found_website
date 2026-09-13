import re
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from database import query_db, execute_db, log_audit, create_notification

# Common English stop words to filter when analyzing keyword overlap
STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "was", "are",
    "were", "this", "that", "it", "my", "item", "lost", "found", "color", "has"
}

def extract_keywords(text):
    """Extract clean lowercase keywords from text, ignoring punctuation and stop words."""
    if not text:
        return set()
    words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
    return {w for w in words if w not in STOP_WORDS}

def text_similarity_ratio(text1, text2):
    """Calculate string similarity ratio between 0.0 and 1.0 using SequenceMatcher."""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, str(text1).strip().lower(), str(text2).strip().lower()).ratio()

def keyword_overlap_count(text1, text2):
    """Count how many significant keywords are shared between two texts."""
    kw1 = extract_keywords(text1)
    kw2 = extract_keywords(text2)
    return len(kw1.intersection(kw2))

def evaluate_claim(claim_id, item_type, item_id, claimant_id, answers_dict, has_evidence=False):
    """
    Rule-based claim evaluation system for MCA decision support.
    Calculates verification score (0 to 100), determines confidence level,
    and flags suspicious patterns.
    """
    score = 0
    score_breakdown = []
    flags = []
    suspicious = False

    # 1. Fetch item information
    if item_type == "lost":
        item = query_db("SELECT * FROM lost_items WHERE id = %s", (item_id,), one=True)
    else:
        item = query_db("SELECT * FROM found_items WHERE id = %s", (item_id,), one=True)

    if not item:
        return {"score": 0, "confidence": "Low Confidence", "suspicious": True, "reasons": ["Item not found"]}

    # 2. Check claimant account status and history
    claimant = query_db("SELECT * FROM users WHERE id = %s", (claimant_id,), one=True)
    if claimant and claimant.get("is_active"):
        score += 5
        score_breakdown.append({"rule": "Active and verified account", "points": 5})

    # Check for multiple claims submitted by this claimant in the last 24 hours
    one_day_ago = datetime.now() - timedelta(days=1)
    recent_claims = query_db(
        "SELECT COUNT(*) AS total FROM claims WHERE claimant_id = %s AND created_at >= %s",
        (claimant_id, one_day_ago),
        one=True
    )
    if recent_claims and recent_claims["total"] >= 3:
        suspicious = True
        flags.append("Claimant submitted 3 or more claims within 24 hours")
        score -= 15
        score_breakdown.append({"rule": "Excessive claims in short timeframe", "points": -15})

    # Check for repeated rejected claims in past 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    rejected_claims = query_db(
        "SELECT COUNT(*) AS total FROM claims WHERE claimant_id = %s AND status = 'Rejected' AND updated_at >= %s",
        (claimant_id, thirty_days_ago),
        one=True
    )
    if rejected_claims and rejected_claims["total"] >= 2:
        suspicious = True
        flags.append("Claimant has 2 or more rejected claims within 30 days")
        score -= 20
        score_breakdown.append({"rule": "History of rejected claims", "points": -20})

    # Check if multiple claimants have filed claims for this specific item
    other_claims = query_db(
        "SELECT COUNT(*) AS total FROM claims WHERE item_type = %s AND item_id = %s AND id != %s AND status != 'Rejected'",
        (item_type, item_id, claim_id),
        one=True
    )
    if other_claims and other_claims["total"] > 0:
        flags.append(f"Multiple claimants ({other_claims['total'] + 1}) have active claims for this item")

    # 3. Analyze claimant answers
    location_ans = answers_dict.get("location_lost", "") or answers_dict.get("location_found", "")
    time_ans = answers_dict.get("time_lost", "") or answers_dict.get("date_lost", "")
    private_feature_ans = answers_dict.get("private_features", "")
    scratches_ans = answers_dict.get("scratches_marks", "")
    accessories_ans = answers_dict.get("accessories", "")
    additional_ans = answers_dict.get("additional_info", "")

    # Compare location
    item_location = item.get("location_lost") or item.get("location_found") or ""
    loc_sim = text_similarity_ratio(location_ans, item_location)
    loc_kw = keyword_overlap_count(location_ans, item_location)

    if loc_sim > 0.4 or loc_kw >= 1:
        score += 15
        score_breakdown.append({"rule": "Location match / consistency", "points": 15})
    elif location_ans.strip():
        score += 5
        score_breakdown.append({"rule": "Location provided but partial match", "points": 5})

    # Compare date proximity
    item_date_val = item.get("date_lost") or item.get("date_found")
    if item_date_val and time_ans:
        try:
            # Check if claimant provided a parseable date
            claimant_date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", time_ans)
            if claimant_date_match:
                claimant_date = datetime.strptime(claimant_date_match.group(1), "%Y-%m-%d").date()
                delta_days = abs((claimant_date - item_date_val).days)
                if delta_days <= 3:
                    score += 10
                    score_breakdown.append({"rule": "Accurate date alignment (within 3 days)", "points": 10})
                elif delta_days <= 10:
                    score += 5
                    score_breakdown.append({"rule": "Approximate date proximity (within 10 days)", "points": 5})
            else:
                score += 5
                score_breakdown.append({"rule": "Approximate date/time description provided", "points": 5})
        except Exception:
            score += 5
            score_breakdown.append({"rule": "Approximate date/time description provided", "points": 5})

    # Compare private identifying details if item is from lost_items
    if item_type == "lost":
        stored_private_detail = item.get("private_identifying_detail", "")
        stored_distinctive = item.get("private_distinctive_characteristic", "")
        stored_contents = item.get("private_contents", "")
        stored_serial = item.get("private_serial_or_id", "")

        # Check private identifying detail
        priv_sim = text_similarity_ratio(private_feature_ans, stored_private_detail)
        priv_kw = keyword_overlap_count(private_feature_ans, stored_private_detail)

        if priv_sim > 0.35 or priv_kw >= 1:
            score += 25
            score_breakdown.append({"rule": "Matching private identifying detail", "points": 25})
        elif len(private_feature_ans.strip()) < 5:
            score -= 10
            score_breakdown.append({"rule": "Evasive or missing private detail", "points": -10})
            flags.append("Claimant provided negligible private identifying information")

        # Check distinctive scratches / marks / serial
        dist_sim = text_similarity_ratio(scratches_ans, stored_distinctive)
        dist_kw = keyword_overlap_count(scratches_ans, stored_distinctive)

        if stored_serial and stored_serial.strip().lower() in scratches_ans.lower() + " " + additional_ans.lower():
            score += 20
            score_breakdown.append({"rule": "Serial number or unique identifier match", "points": 20})
        elif dist_sim > 0.35 or dist_kw >= 1:
            score += 20
            score_breakdown.append({"rule": "Matching distinctive markings or characteristics", "points": 20})
        elif len(scratches_ans.strip()) > 10:
            score += 10
            score_breakdown.append({"rule": "Detailed scratch/marking descriptions provided", "points": 10})

        # Check if claimant only copied public description
        public_desc = item.get("description", "")
        desc_sim = text_similarity_ratio(private_feature_ans, public_desc)
        if desc_sim > 0.75 and len(public_desc) > 20:
            suspicious = True
            flags.append("Claimant answer strongly resembles publicly visible item description")
            score -= 10
            score_breakdown.append({"rule": "Claimant repeating public description", "points": -10})

    else:
        # Found items evaluation
        # Claimant must describe items not visible in public listing
        if len(private_feature_ans.strip()) >= 15:
            score += 25
            score_breakdown.append({"rule": "Substantive private feature description", "points": 25})
        elif len(private_feature_ans.strip()) < 5:
            score -= 10
            score_breakdown.append({"rule": "Lacks specific identifying features", "points": -10})
            flags.append("Claimant failed to describe distinct non-public features")

        if len(scratches_ans.strip()) >= 10:
            score += 20
            score_breakdown.append({"rule": "Distinctive marks/scratches provided", "points": 20})

    # Check accessories
    if len(accessories_ans.strip()) >= 8:
        score += 10
        score_breakdown.append({"rule": "Associated accessories detailed", "points": 10})

    # Check ownership evidence uploaded
    if has_evidence:
        score += 20
        score_breakdown.append({"rule": "Valid ownership proof/receipt submitted", "points": 20})

    # Clamp score between 0 and 100
    final_score = max(0, min(100, score))

    # Determine confidence level based on score
    if final_score >= 80:
        confidence = "Strong Verification"
    elif final_score >= 60:
        confidence = "Needs Review"
    else:
        confidence = "Low Confidence"

    if confidence == "Low Confidence" or flags:
        suspicious = True

    # Save to verification_results table
    import json
    breakdown_json = json.dumps(score_breakdown)
    flags_json = json.dumps(flags)

    existing = query_db("SELECT id FROM verification_results WHERE claim_id = %s", (claim_id,), one=True)
    if existing:
        execute_db(
            """
            UPDATE verification_results
            SET score = %s, score_breakdown = %s, confidence_level = %s, flags = %s, calculated_at = CURRENT_TIMESTAMP
            WHERE claim_id = %s
            """,
            (final_score, breakdown_json, confidence, flags_json, claim_id)
        )
    else:
        execute_db(
            """
            INSERT INTO verification_results (claim_id, score, score_breakdown, confidence_level, flags)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (claim_id, final_score, breakdown_json, confidence, flags_json)
        )

    # Update claims table with summary
    execute_db(
        """
        UPDATE claims
        SET verification_score = %s, confidence_level = %s, suspicious_flag = %s, suspicious_reasons = %s
        WHERE id = %s
        """,
        (final_score, confidence, 1 if suspicious else 0, "; ".join(flags) if flags else None, claim_id)
    )

    return {
        "score": final_score,
        "confidence": confidence,
        "suspicious": suspicious,
        "flags": flags,
        "breakdown": score_breakdown
    }

def find_potential_matches(item_type, item_data, limit=5):
    """
    Rule-based matching algorithm to suggest matches between lost and found items.
    MCA student friendly logic using category, keyword overlap, location, and date proximity.
    """
    category_id = item_data.get("category_id")
    target_date = item_data.get("date_lost") or item_data.get("date_found")
    item_name = item_data.get("item_name", "")
    description = item_data.get("description", "")
    location = item_data.get("location_lost") or item_data.get("location_found") or ""

    # Search opposite table
    if item_type == "lost":
        table = "found_items"
        date_col = "date_found"
        loc_col = "location_found"
    else:
        table = "lost_items"
        date_col = "date_lost"
        loc_col = "location_lost"

    # Query active candidates in same category or adjacent
    candidates = query_db(
        f"""
        SELECT f.*, c.name AS category_name
        FROM {table} f
        JOIN categories c ON f.category_id = c.id
        WHERE f.status IN ('Active', 'Claim Pending', 'Under Verification')
          AND f.id != %s
        ORDER BY f.created_at DESC
        LIMIT 50
        """,
        (item_data.get("id", 0),)
    )

    matches = []
    item_keywords = extract_keywords(item_name + " " + description)
    loc_keywords = extract_keywords(location)

    for cand in candidates:
        match_score = 0
        match_reasons = []

        # 1. Category match
        if cand.get("category_id") == category_id:
            match_score += 40
            match_reasons.append("Same category")

        # 2. Name & description keyword overlap
        cand_text = cand.get("item_name", "") + " " + cand.get("description", "")
        cand_keywords = extract_keywords(cand_text)
        shared_kw = item_keywords.intersection(cand_keywords)
        if len(shared_kw) >= 3:
            match_score += 30
            match_reasons.append(f"{len(shared_kw)} keyword matches")
        elif len(shared_kw) >= 1:
            match_score += 15
            match_reasons.append(f"{len(shared_kw)} keyword match")

        # 3. Location overlap
        cand_loc = cand.get(loc_col, "")
        cand_loc_keywords = extract_keywords(cand_loc)
        shared_loc = loc_keywords.intersection(cand_loc_keywords)
        if shared_loc:
            match_score += 15
            match_reasons.append("Location alignment")

        # 4. Date proximity within 14 days
        cand_date = cand.get(date_col)
        if target_date and cand_date:
            try:
                days_diff = abs((target_date - cand_date).days)
                if days_diff <= 7:
                    match_score += 15
                    match_reasons.append("Within 7 days")
                elif days_diff <= 14:
                    match_score += 10
                    match_reasons.append("Within 14 days")
            except Exception:
                pass

        if match_score >= 35:
            matches.append({
                "item": cand,
                "score": match_score,
                "reasons": match_reasons
            })

    # Sort matches by score descending
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:limit]
