def aggregate_quant_sentiment(sentence_scores, is_headline_first=True):
    """
    Processes a raw array of sentence float predictions [-1.0 to 1.0].
    Applies noise density filters, positional anchors, and asymmetric downside weights.
    Returns a structured dictionary mapping the quantitative risk profile.
    """
    if not sentence_scores:
        return {"final_average": 0.0, "max_upside_signal": 0.0, "max_downside_signal": 0.0}

    weighted_scores = []
    
    # Extract baseline math extremes across all parsed sentences
    max_upside = max(sentence_scores)
    max_downside = min(sentence_scores)
    
    for i, score in enumerate(sentence_scores):
        
        # RULE 1: SENTIMENT DENSITY FILTER
        # Eliminate passive, neutral, or non-signal expressions (-0.1 to 0.1)
        if abs(score) <= 0.1:
            continue
            
        weight = 1.0
        
        # RULE 2: POSITIONAL ANCHORING (The Journalism Rule)
        if i == 0 and is_headline_first:
            weight = 1.5  # Heavy structural leverage to lead context
        elif i == len(sentence_scores) - 1:
            weight = 1.2  # Enhanced priority given to the concluding premise
            
        # RULE 3: MAGNITUDE POOLING
        # Amplifies high-impact phrases while shrinking shallow variations
        magnitude_multiplier = 1.0 + abs(score) 
        
        # RULE 4: ASYMMETRIC RISK PENALTY
        # Underwriting safety protocol: penalize negative signals by an extra 1.5x
        if score < 0:
            weight *= 1.5
        
        # Combine parameters safely
        final_sentence_weight = weight * magnitude_multiplier
        weighted_scores.append((score * final_sentence_weight, final_sentence_weight))
        
    # Fallback if the article contained 100% neutral noise text
    if not weighted_scores:
        return {
            "final_average": 0.0, 
            "max_upside_signal": round(max_upside, 3), 
            "max_downside_signal": round(max_downside, 3)
        }
        
    # Calculate the definitive weighted mathematical balance
    total_score = sum(item[0] for item in weighted_scores)
    total_weight = sum(item[1] for item in weighted_scores)
    
    final_average = total_score / total_weight
    
    # Cap boundaries strictly to the mathematical range [-1.0, 1.0]
    final_average = max(-1.0, min(1.0, final_average))
    
    return {
        "final_average": round(final_average, 3),
        "max_upside_signal": round(max_upside, 3),
        "max_downside_signal": round(max_downside, 3)
    }