import json
import os
import numpy as np
import cv2
import supervision as sv
from supervision.annotators.utils import (
    resolve_color,
    resolve_text_background_xyxy,
)
from typing import Optional, Tuple
from supervision.annotators.base import ImageType
from typing import List
from supervision.detection.core import Detections

def draw_crowd(frame, crowds, color="#fbdd00"):
    color = sv.Color.from_hex(color).as_bgr()
    for crowd in crowds:
        cv2.circle(frame, (crowd[0], crowd[1]), crowd[2], color, 2)
    return frame

def get_zone_annotator(zone):
    zone_annotators = sv.PolygonZoneAnnotator(
        zone=zone,
        thickness=2,
        text_thickness=0,
        text_scale=0,
        text_padding=0,
        color=sv.ColorPalette.DEFAULT.by_idx(1),
    ) 
    return zone_annotators


def get_box_annotator(type=None):
    return sv.RoundBoxAnnotator() 


class DrawerObject:
    def __init__(self):
        self.line = []
        self.line_annotator = []
        self.box_annotator = None
        self.zone_annotator = []
        self.zone_rectangle = []
        self.zone_center = []
        self.zone_bottom_center = []
        self.zone_annotator = []
        self.zone = []


class ServicesDrawer:
    def __init__(self, service_info):

        self.drawer = {
            "crowd_detection": None,
            "vehicle_counting": None,
            "reidentify": None,
            "license_plate": None,
            "speed_estimate": None,

        }
        for service_name, metadata in service_info.items():
            if service_name in self.drawer:
                self.init_draw(service_name, metadata)

    def init_draw(self, service_name, metadata):
        drawer = DrawerObject()
        drawer.box_annotator = get_box_annotator()
        for polygons in metadata["polygons"]:
            if polygons:
                zone = np.array(polygons).astype(int)
                zone_center = sv.PolygonZone(
                    polygon=zone, triggering_anchors=[sv.Position.CENTER]
                )

                zone_bottom_center = sv.PolygonZone(
                    polygon=zone,
                    triggering_anchors=[sv.Position.BOTTOM_CENTER],
                )

                zone_rectangle = sv.PolygonZone(
                    polygon=zone,
                    triggering_anchors=[
                        sv.Position.TOP_LEFT,
                        sv.Position.BOTTOM_LEFT,
                        sv.Position.TOP_RIGHT,
                        sv.Position.BOTTOM_RIGHT,
                    ],
                )
                zone_annotator = get_zone_annotator(zone_center)  #

                drawer.zone_annotator.append(zone_annotator)
                drawer.zone_rectangle.append(zone_rectangle)
                drawer.zone_center.append(zone_center)
                drawer.zone_bottom_center.append(zone_bottom_center)
                drawer.zone.append(zone)
        for lines in metadata["lines"]:
            if lines:
                line_start = sv.Point(*lines[0])
                line_end = sv.Point(*lines[1])
                line = LineZoneCustom(
                    start=line_start,
                    end=line_end,
                    triggering_anchors=[sv.Position.CENTER],
                )
        
                line_annotator = sv.LineZoneAnnotator()

                drawer.line_annotator.append(line_annotator)
                drawer.line.append(line)

        self.drawer[service_name] = drawer
        

class LineZoneCustom(sv.LineZone):
    def __init__(self, start: sv.Point, end: sv.Point, triggering_anchors: List[sv.Position], direction:list = []):
        super().__init__(start, end, triggering_anchors)
        self.name = "Line-1"
        self.direction = direction


class CustomLabelAnnotator(sv.LabelAnnotator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_text_scale = self.text_scale
        self.base_text_padding = self.text_padding
        self.base_text_thickness = self.text_thickness
        self.baseline_size = 640

    def annotate(
        self,
        scene: ImageType,
        detections: Detections,
        labels: List[str] = None,
        custom_color_lookup: Optional[np.ndarray] = None,
        alpha: float = 0.7,  
    ) -> ImageType:
        font = cv2.FONT_HERSHEY_SIMPLEX
        height, width = scene.shape[:2]
        scale_factor = min(width, height) / self.baseline_size

        self.text_scale = self.base_text_scale * scale_factor
        self.text_padding = max(1, int(self.base_text_padding * scale_factor))
        self.text_thickness = max(1, int(self.text_thickness * scale_factor))
        
        anchors_coordinates = detections.get_anchors_coordinates(
            anchor=self.text_anchor
        ).astype(int)
        
        if labels is not None and len(labels) != len(detections):
            raise ValueError(
                f"Labels count ({len(labels)}) doesn't match detections ({len(detections)})"
            )

        try:
            for detection_idx, center_coordinates in enumerate(anchors_coordinates):
                color = resolve_color(
                    color=self.color,
                    detections=detections,
                    detection_idx=detection_idx,
                    color_lookup=custom_color_lookup or self.color_lookup,
                )

                # Get text for current detection
                if labels is not None:
                    text = labels[detection_idx]
                elif detections.class_names is not None:
                    text = detections.class_names[detection_idx]
                else:
                    text = str(detection_idx)

                # Process multiline text
                lines = text.split('\n')
                max_width = 0
                total_height = 0
                line_heights = []

                for line in lines:
                    (w, h), _ = cv2.getTextSize(
                        text=line,
                        fontFace=font,
                        fontScale=self.text_scale,
                        thickness=self.text_thickness,
                    )
                    max_width = max(max_width, w)
                    total_height += h
                    line_heights.append(h)

                # Add padding between lines
                total_height += (len(lines) - 1) * self.text_padding

                # Calculate background dimensions
                text_w_padded = max_width + 2 * self.text_padding
                text_h_padded = total_height + 2 * self.text_padding
                
                text_background_xyxy = resolve_text_background_xyxy(
                    center_coordinates=tuple(center_coordinates),
                    text_wh=(text_w_padded, text_h_padded),
                    position=self.text_anchor,
                )

                # Draw transparent background
                self.draw_rounded_rectangle_with_alpha(
                    scene=scene,
                    xyxy=text_background_xyxy,
                    color=color,
                    alpha=alpha, 
                )

                # Draw each line
                current_y = text_background_xyxy[1] + self.text_padding
                for line, height in zip(lines, line_heights):
                    cv2.putText(
                        img=scene,
                        text=line,
                        org=(text_background_xyxy[0] + self.text_padding, current_y + height),
                        fontFace=font,
                        fontScale=self.text_scale,
                        color=self.text_color.as_bgr(),
                        thickness=self.text_thickness,
                        lineType=cv2.LINE_AA,
                    )
                    current_y += height + self.text_padding

            return scene
        finally:
            self.text_scale = self.base_text_scale
            self.text_padding = self.base_text_padding
            self.text_thickness = self.base_text_thickness

    def draw_rounded_rectangle_with_alpha(
        self, scene: ImageType, xyxy: Tuple[int, int, int, int], color: sv.Color, alpha: float
    ):
        """
        Draws a rounded rectangle with transparency (alpha blending).

        Args:
            scene (ImageType): The scene/image.
            xyxy (Tuple[int, int, int, int]): Top-left and bottom-right coordinates of the rectangle.
            color (sv.Color): The color of the rectangle.
            alpha (float): The transparency level (0.0 to 1.0).
            border_radius (int): The radius of the rectangle corners.
        """
        overlay = scene.copy()
        top_left, bottom_right = (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3])
        cv2.rectangle(
            overlay,
            top_left,
            bottom_right,
            color.as_bgr(),
            thickness=-1,
        )
        # Blend the overlay with the original scene
        cv2.addWeighted(overlay, alpha, scene, 1 - alpha, 0, dst=scene)