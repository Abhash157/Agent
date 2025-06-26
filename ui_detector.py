import cv2
import numpy as np
import logging

logger = logging.getLogger("UIDetector")

def detect_ui_elements(image):
    """
    Detect UI elements using multiple approaches.
    
    Args:
        image: OpenCV image in BGR format
        
    Returns:
        processed_img: Image with detected elements highlighted
        elements: List of (x, y, w, h) tuples for detected elements
    """
    if image is None:
        return None, []
    
    # Make a copy of the input image for drawing
    processed_img = image.copy()
    all_elements = []
    
    # Approach 1: Color-based segmentation for buttons and UI elements
    color_elements = detect_by_color(image)
    
    # Approach 2: Edge-based detection for rectangular elements
    edge_elements = detect_by_edges(image)
    
    # Approach 3: Text region detection
    text_elements = detect_text_regions(image)
    
    # Combine all detected elements
    all_elements = color_elements + edge_elements + text_elements
    
    # Remove overlapping elements
    all_elements = remove_overlaps(all_elements)
    
    # Draw all detected elements on the processed image
    for i, (x, y, w, h) in enumerate(all_elements):
        cv2.rectangle(processed_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(processed_img, str(i), (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    logger.info(f"Detected {len(all_elements)} UI elements")
    return processed_img, all_elements

def detect_by_color(image):
    """Detect UI elements based on color segmentation."""
    elements = []
    
    # Convert to HSV for better color segmentation
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Define color ranges for common UI elements (buttons, input fields)
    # These ranges should be adjusted based on your desktop theme
    
    # Light gray/white elements (input fields, dialogs)
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([180, 30, 255])
    
    # Blue elements (buttons, links)
    lower_blue = np.array([100, 50, 50])
    upper_blue = np.array([140, 255, 255])
    
    # Gray elements (buttons, panels)
    lower_gray = np.array([0, 0, 100])
    upper_gray = np.array([180, 30, 190])
    
    # Create masks
    mask_white = cv2.inRange(hsv, lower_white, upper_white)
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    mask_gray = cv2.inRange(hsv, lower_gray, upper_gray)
    
    # Combine masks
    combined_mask = cv2.bitwise_or(mask_white, mask_blue)
    combined_mask = cv2.bitwise_or(combined_mask, mask_gray)
    
    # Find contours in the combined mask
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Process each contour
    for cnt in contours:
        # Filter by area
        area = cv2.contourArea(cnt)
        if area < 100:  # Minimum area threshold
            continue
        
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Filter by aspect ratio
        aspect_ratio = w / float(h) if h > 0 else 0
        if aspect_ratio < 0.1 or aspect_ratio > 15:
            continue
        
        elements.append((x, y, w, h))
    
    return elements

def detect_by_edges(image):
    """Detect UI elements based on edge detection."""
    elements = []
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection
    edges = cv2.Canny(blurred, 30, 100)
    
    # Dilate edges to connect nearby edges
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Process each contour
    for cnt in contours:
        # Approximate the contour to simplify
        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        
        # Check if it's approximately rectangular (4 points)
        if len(approx) >= 4 and len(approx) <= 6:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Filter by area
            area = w * h
            if area < 200:  # Minimum area threshold
                continue
            
            # Filter by aspect ratio
            aspect_ratio = w / float(h) if h > 0 else 0
            if aspect_ratio < 0.1 or aspect_ratio > 15:
                continue
            
            elements.append((x, y, w, h))
    
    return elements

def detect_text_regions(image):
    """Detect potential text regions which might be UI elements."""
    elements = []
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 11, 2)
    
    # Create a horizontal kernel and detect horizontal lines
    h_kernel = np.ones((1, 15), np.uint8)
    h_dilate = cv2.dilate(thresh, h_kernel, iterations=1)
    
    # Create a vertical kernel and detect vertical lines
    v_kernel = np.ones((15, 1), np.uint8)
    v_dilate = cv2.dilate(thresh, v_kernel, iterations=1)
    
    # Combine horizontal and vertical lines
    combined = cv2.bitwise_or(h_dilate, v_dilate)
    
    # Find contours
    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Process each contour
    for cnt in contours:
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Filter by area
        area = w * h
        if area < 200 or area > 50000:  # Area thresholds
            continue
        
        # Filter by aspect ratio
        aspect_ratio = w / float(h) if h > 0 else 0
        if aspect_ratio < 0.1 or aspect_ratio > 15:
            continue
        
        elements.append((x, y, w, h))
    
    return elements

def remove_overlaps(elements, overlap_threshold=0.7):
    """Remove overlapping elements."""
    if not elements:
        return []
    
    # Sort elements by area (largest first)
    elements.sort(key=lambda elem: elem[2] * elem[3], reverse=True)
    
    filtered_elements = []
    
    for elem in elements:
        x1, y1, w1, h1 = elem
        should_add = True
        
        for filtered_elem in filtered_elements:
            x2, y2, w2, h2 = filtered_elem
            
            # Calculate intersection area
            x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            overlap_area = x_overlap * y_overlap
            
            # Calculate areas
            area1 = w1 * h1
            area2 = w2 * h2
            smaller_area = min(area1, area2)
            
            # Check if overlap is significant
            if overlap_area > 0 and overlap_area / smaller_area > overlap_threshold:
                should_add = False
                break
        
        if should_add:
            filtered_elements.append(elem)
    
    return filtered_elements 