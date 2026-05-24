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
            
    for section in study_pack.get("sections", []):
        corrected_assets = []
        raw_embedded = section.get("embedded_assets", [])
        if not isinstance(raw_embedded, list):
            raw_embedded = []
            
        for asset in raw_embedded:
            if not asset or not isinstance(asset, str):
                continue
                
            matched = False
            # Find the position of 'img_'
            idx = asset.lower().find("img_")
            if idx != -1:
                # Extract suffix starting from 'img_' or check if docx_img / pptx_img prefix is there
                # e.g. for "jobid_docx_img_1.png", search for docx_img or pptx_img first
                suffix = asset[idx:]
                # Check if there is docx_ or pptx_ before it
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
                    # Fuzzy match suffix
                    for skey, sval in suffix_map.items():
                        if suffix_clean in skey or skey in suffix_clean:
                            corrected_assets.append(sval)
                            matched = True
                            logger.info(f"Fuzzy corrected asset typo '{asset}' to '{sval}'")
                            break
                            
            if not matched:
                # If we have only one actual asset, map to it as fallback
                if len(actual_assets) == 1:
                    corrected_assets.append(actual_assets[0])
                    logger.info(f"Fallback matched asset to single actual asset '{actual_assets[0]}'")
                else:
                    # Keep raw as fallback
                    corrected_assets.append(asset)
                    
        section["embedded_assets"] = corrected_assets
