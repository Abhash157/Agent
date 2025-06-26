import Xlib
import Xlib.display
import pyautogui
import cv2
import numpy as np
import time
import traceback
from PIL import Image
import pytesseract

# --- Define your function for internal processing ---
def find_internal_containers(window_image_cv):
    # Ensure the input image is not None
    if window_image_cv is None:
        return None, []

    gray = cv2.cvtColor(window_image_cv, cv2.COLOR_BGR2GRAY)
    # You might need to adjust these thresholds based on image contrast
    edges = cv2.Canny(gray, 30, 100) # Lower thresholds for more edge detection

    # Use copy() to avoid modifying the original edges image in findContours
    contours, hierarchy = cv2.findContours(edges.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    output_img = window_image_cv.copy()
    container_rects = []

    if hierarchy is not None:
        hierarchy = hierarchy[0] # Get the actual hierarchy array
        for i, cnt in enumerate(contours):
            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)

            # Check if the contour is approximately rectangular
            if len(approx) == 4:
                x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)

                # Adjust these filtering criteria based on your target "containers"
                min_area = 500 # Reduced threshold to detect smaller UI elements
                aspect_ratio = w_c / float(h_c) if h_c > 0 else 0

                # Example filters (tune these based on what you want to detect)
                if cv2.contourArea(cnt) > min_area and 0.1 < aspect_ratio < 15.0:
                    # Check hierarchy[i][3] to see if it has a parent (is nested)? (Optional advanced filter)
                    # if hierarchy[i][3] != -1: # Example: only detect nested contours

                    # Draw the rectangle with a different color (Blue) and thicker line
                    contour_color = (255, 0, 0) # Blue in BGR format
                    line_thickness = 3 # Increased thickness

                    cv2.rectangle(output_img, (x_c, y_c), (x_c + w_c, y_c + h_c), contour_color, line_thickness)
                    container_rects.append((x_c, y_c, w_c, h_c))
                    # Draw contour index text
                    cv2.putText(output_img, str(i), (x_c, y_c - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, contour_color, 1)

    return output_img, container_rects
# --- End of internal processing function ---


try:
    display = Xlib.display.Display()
    root = display.screen().root
    # Use _NET_CLIENT_LIST_STACKING for potentially a more ordered list,
    # but _NET_CLIENT_LIST is usually sufficient for iterating windows.
    window_ids = root.get_full_property(display.intern_atom('_NET_CLIENT_LIST'), Xlib.X.AnyPropertyType)
    if window_ids:
        window_ids = window_ids.value
    else:
         window_ids = []
         print("Warning: No window IDs found in _NET_CLIENT_LIST.")


    for window_id in window_ids:
        try:
            window = display.create_resource_object('window', window_id)
            attrs = window.get_attributes()

            # Check if the window is viewable before getting geometry
            if attrs.map_state != Xlib.X.IsViewable:
                # print(f"Skipping non-viewable window ID {window_id}")
                continue

            # Use translate_coords for reliable absolute position
            coords = window.translate_coords(root, 0, 0)
            x_abs = coords.x
            y_abs = coords.y

            geom = window.get_geometry()

            # Use absolute coordinates and geometry width/height
            x, y, width, height = x_abs, y_abs, geom.width, geom.height

            # Fetch title safely (cleaned up)
            title_prop = window.get_wm_name()
            window_title = title_prop if title_prop else "Untitled"

            # Filter based on size and potentially position (e.g., ignore off-screen)
            # Adjust filters as needed to include/exclude specific windows
            if width > 100 and height > 100 and x >= 0 and y >= 0:
                print(f"Processing window: '{window_title}' (ID: {window_id}) Geom: {x},{y} {width}x{height}")

                # Add a small delay if screenshots are blank/incorrect on your system
                time.sleep(0.1)

                # Take screenshot of the window region using absolute coords
                # Ensure pyautogui handles potential off-by-one or boundary issues
                region = (max(0, x), max(0, y), width, height) # Ensure non-negative coords

                try:
                    window_screenshot_pil = pyautogui.screenshot(region=region)
                except Exception as screenshot_error:
                    print(f"  -> Failed to take screenshot for region {region}: {screenshot_error}")
                    continue


                if window_screenshot_pil is None or window_screenshot_pil.size[0] == 0 or window_screenshot_pil.size[1] == 0:
                     print(f"  -> Failed to get valid screenshot for region {region}")
                     continue

                window_screenshot_cv = cv2.cvtColor(np.array(window_screenshot_pil), cv2.COLOR_RGB2BGR)

               # Process the individual window screenshot
                processed_window_img, internal_boxes = find_internal_containers(window_screenshot_cv)

                # Check if processed_window_img is valid before displaying/saving
                if processed_window_img is None:
                     print(f"  -> find_internal_containers returned None for window ID {window_id}")
                     continue

                # Perform OCR on the found internal boxes
                for i, (x_c, y_c, w_c, h_c) in enumerate(internal_boxes):
                    try:
                        # Crop the region from original PIL image (RGB)
                        # Use the coordinates relative to the window screenshot (x_c, y_c)
                        roi = window_screenshot_pil.crop((x_c, y_c, x_c + w_c, y_c + h_c))
                        text = pytesseract.image_to_string(roi)
                        if text.strip(): # Only print if text is found
                            print(f"  OCR for box {i} (relative coords {x_c},{y_c} {w_c}x{h_c}): {text.strip()}")
                    except Exception as ocr_error:
                        print(f"  Error in OCR for box {i}: {ocr_error}")


                # Display or save the result for this window
                # Limit title length for display window title
                display_title = f"Contents: {window_title[:50]}" if window_title else f"Contents: ID {window_id}"
                cv2.imshow(display_title, processed_window_img)
                cv2.imwrite(f"window_{window_id}_processed.png", processed_window_img)

        except (Xlib.error.BadWindow, Xlib.error.BadDrawable, Xlib.error.BadMatch, AttributeError, TypeError) as e:
             # Catching potential errors during property access or window interaction
             print(f"--- Error processing window ID {window_id} ---")
             traceback.print_exc() # Print full error information
             print(f"--- End error for window ID {window_id} ---")
             continue # Skip windows that cause specific Xlib or attribute errors
        except Exception as e:
             # Catch any other unexpected errors during the processing of a single window
             print(f"--- Unexpected error processing window ID {window_id} ---")
             traceback.print_exc()
             print(f"--- End unexpected error for window ID {window_id} ---")
             continue


except Exception as e:
    print(f"An unexpected error occurred during initial setup or window listing: {e}")
    traceback.print_exc()
    print("Ensure you are running an X11 session and have python-xlib, pyautogui, opencv-python, Pillow, and pytesseract installed.")

finally:
    # Keep windows open until a key is pressed
    print("Press any key in any OpenCV window to exit.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()