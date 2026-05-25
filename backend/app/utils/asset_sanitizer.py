from app.utils.logger import logger

def sanitize_embedded_assets(study_pack: dict, actual_job_id: str, actual_assets: list):
    """
    Corrects any UUID transcription or typo errors in embedded_assets filenames
    using the list of actual extracted assets from the document.
    """
    if not study_pack or not actual_assets:
        return
        
    logger.info(f"Sanitizing study pack embedded assets for job {actual_job_id}. Actual assets count: {len(actual_assets)}")
    
    # Create mapping from suffix -> actual filename
    suffix_map = {}
    for asset in actual_assets:
        # Find the suffix after the job_id prefix (UUID prefix of 36 chars + 1 underscore)
        if len(asset) > 37:
            # Suffix starts after the job_id (length 36) and underscore
            suffix = asset[37:]  # e.g., "img_1.png", "docx_img_1.png", "pptx_img_1.png"
            suffix_map[suffix.lower()] = asset
            
    logger.debug(f"Asset suffix map: {suffix_map}")
            
    # 1. Sanitize sections (for STUDY_PACK mode)
    for section in study_pack.get("sections", []):
        corrected_assets = []
        raw_embedded = section.get("embedded_assets", [])
        if not isinstance(raw_embedded, list):
            raw_embedded = []
            
        for asset in raw_embedded:
            if not asset or not isinstance(asset, str):
                continue
                
            matched = False
            idx = asset.lower().find("img_")
            if idx != -1:
                suffix = asset[idx:]
                before_idx = asset.lower().find("docx_img_")
                if before_idx != -1:
                    suffix = asset[before_idx:]
                else:
                    before_idx = asset.lower().find("pptx_img_")
                    if before_idx != -1:
                        suffix = asset[before_idx:]
                        
                suffix_clean = suffix.lower()
                if suffix_clean in suffix_map:
                    corrected_assets.append(suffix_map[suffix_clean])
                    matched = True
                    logger.info(f"Corrected asset typo '{asset}' to '{suffix_map[suffix_clean]}'")
                else:
                    for skey, sval in suffix_map.items():
                        if suffix_clean in skey or skey in suffix_clean:
                            corrected_assets.append(sval)
                            matched = True
                            logger.info(f"Fuzzy corrected asset typo '{asset}' to '{sval}'")
                            break
                            
            if not matched:
                if len(actual_assets) == 1:
                    corrected_assets.append(actual_assets[0])
                    logger.info(f"Fallback matched asset to single actual asset '{actual_assets[0]}'")
                else:
                    corrected_assets.append(asset)
                    
        section["embedded_assets"] = corrected_assets

    # 2. Sanitize questions (for ANSWER_PACK mode)
    for question in study_pack.get("questions", []):
        corrected_assets = []
        raw_embedded = question.get("related_assets", [])
        if not raw_embedded:
            raw_embedded = question.get("embedded_assets", [])
        if not isinstance(raw_embedded, list):
            raw_embedded = []
            
        for asset in raw_embedded:
            if not asset or not isinstance(asset, str):
                continue
                
            matched = False
            idx = asset.lower().find("img_")
            if idx != -1:
                suffix = asset[idx:]
                before_idx = asset.lower().find("docx_img_")
                if before_idx != -1:
                    suffix = asset[before_idx:]
                else:
                    before_idx = asset.lower().find("pptx_img_")
                    if before_idx != -1:
                        suffix = asset[before_idx:]
                        
                suffix_clean = suffix.lower()
                if suffix_clean in suffix_map:
                    corrected_assets.append(suffix_map[suffix_clean])
                    matched = True
                    logger.info(f"Corrected asset typo '{asset}' to '{suffix_map[suffix_clean]}'")
                else:
                    for skey, sval in suffix_map.items():
                        if suffix_clean in skey or skey in suffix_clean:
                            corrected_assets.append(sval)
                            matched = True
                            logger.info(f"Fuzzy corrected asset typo '{asset}' to '{sval}'")
                            break
                            
            if not matched:
                if len(actual_assets) == 1:
                    corrected_assets.append(actual_assets[0])
                    logger.info(f"Fallback matched asset to single actual asset '{actual_assets[0]}'")
                else:
                    corrected_assets.append(asset)
                    
        question["related_assets"] = corrected_assets
        question["embedded_assets"] = corrected_assets
