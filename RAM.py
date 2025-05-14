import Xlib
import Xlib.display
import pyautogui
import cv2
import numpy as np
import time
import traceback # Import traceback
from PIL import Image
import pytesseract

# --- Define your function for internal processing (same as before) ---
def find_internal_containers(window_image_cv):
    # (Your refined OpenCV code from the previous example goes here)
    gray = cv2.cvtColor(window_image_cv, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150) # Adjust thresholds as needed
    contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    output_img = window_image_cv.copy()
    container_rects = []
    if hierarchy is not None:
        hierarchy = hierarchy[0] # Get the actual hierarchy array
        for i, cnt in enumerate(contours):
            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
            if len(approx) == 4:  # Looks like a rectangle
                x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
                min_area = 5000
                aspect_ratio = w_c / float(h_c) if h_c > 0 else 0
                if cv2.contourArea(cnt) > min_area and 0.2 < aspect_ratio < 10.0:
                    # Maybe check hierarchy[i][3] to see if it has a parent (is nested)?
                    cv2.rectangle(output_img, (x_c, y_c), (x_c + w_c, y_c + h_c), (0, 255, 0), 2)
                    container_rects.append((x_c, y_c, w_c, h_c))
                    cv2.putText(output_img, str(i), (x_c, y_c - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return output_img, container_rects

# --- End of internal processing function ---


try:
    display = Xlib.display.Display()
    root = display.screen().root
    window_ids = root.get_full_property(display.intern_atom('_NET_CLIENT_LIST'), Xlib.X.AnyPropertyType).value

    if not window_ids:
        print("Warning: No window IDs found in _NET_CLIENT_LIST.")

    for window_id in window_ids:
        try:
            window = display.create_resource_object('window', window_id)
            attrs = window.get_attributes()

            # Check if the window is viewable before getting geometry
            if attrs.map_state != Xlib.X.IsViewable:
                # print(f"Skipping non-viewable window ID {window_id}")
                continue

            geom = window.get_geometry()

            # *** Removed the coordinate translation loop ***
            # We now assume geom.x, geom.y are usable, potentially root-relative
            # or relative to a direct parent we don't need to traverse further back from.

            # Let's try fetching the absolute coordinates using translate_coords
            # This asks "where does the point (0,0) inside this window appear on the root window?"
            coords = window.translate_coords(root, 0, 0)
            x_abs = coords.x
            y_abs = coords.y

            # Use absolute coordinates and geometry width/height
            x, y, width, height = x_abs, y_abs, geom.width, geom.height

            # Fetch title safely
            title_prop = window.get_wm_name()
            window_title = title_prop if title_prop else "Untitled" # Use the result from get_wm_name, default to "Untitled" if empty/None
            
            # Filter based on size and potentially position (e.g., ignore off-screen)
            if width > 100 and height > 100 and x >= 0 and y >= 0 : # Adjust filters as needed
                print(f"Processing window: '{window_title}' (ID: {window_id}) Geom: {x},{y} {width}x{height}")

                # Add a small delay if screenshots are blank/incorrect
                time.sleep(0.1)

                # Take screenshot of the window region using absolute coords
                # Ensure pyautogui handles potential off-by-one or boundary issues
                region = (max(0, x), max(0, y), width, height) # Ensure non-negative coords
                window_screenshot_pil = pyautogui.screenshot(region=region)

                if window_screenshot_pil is None or window_screenshot_pil.size[0] == 0 or window_screenshot_pil.size[1] == 0:
                     print(f"  -> Failed to get valid screenshot for region {region}")
                     continue

                window_screenshot_cv = cv2.cvtColor(np.array(window_screenshot_pil), cv2.COLOR_RGB2BGR)
               # Process the individual window screenshot 
                processed_window_img, internal_boxes = find_internal_containers(window_screenshot_cv)
 

                for i, (x_c, y_c, w_c, h_c) in enumerate(internal_boxes):
                    try:
                        # Crop the region from original PIL image (RGB)
                        roi = window_screenshot_pil.crop((x_c, y_c, x_c + w_c, y_c + h_c))
                        text = pytesseract.image_to_string(roi)
                        print(f"OCR for box {i}: {text.strip()}")
                    except Exception as ocr_error:
                        print(f"Error in OCR for box {i}: {ocr_error}")


                # Display or save the result for this window
                cv2.imshow(f"Contents: {window_title[:50]}", processed_window_img) # Limit title length
                cv2.imwrite(f"window_{window_id}_processed.png", processed_window_img)
    
        except (Xlib.error.BadWindow, Xlib.error.BadDrawable, Xlib.error.BadMatch, AttributeError, TypeError) as e:
             # Catching more potential errors during property access
             # Use the improved error reporting if needed:
             print(f"--- Error processing window ID {window_id} ---")
             traceback.print_exc() # Print full error information
             print(f"--- End error for window ID {window_id} ---")
             continue # Skip windows that might have disappeared or lack properties

except Exception as e:
    print(f"An unexpected error occurred: {e}")
    traceback.print_exc()
    print("Ensure you are running an X11 session and have python-xlib installed.")

finally:
    # Keep windows open until a key is pressed
    print("Press any key in an OpenCV window to exit.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()