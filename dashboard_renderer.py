"""Layout and card rendering for the modular dashboard."""

from PIL import Image, ImageColor, ImageDraw, ImageFont


class DashboardRenderer:
    def __init__(self, disp, cfg, card_builders, logger):
        self.disp = disp
        self.cfg = cfg
        self.card_builders = card_builders
        self.logger = logger

        self.width = disp.height
        self.height = disp.width
        self.rows = int(getattr(cfg, "GRID_ROWS", 3))
        self.cols = int(getattr(cfg, "GRID_COLS", 3))
        self.cell_width = self.width / self.cols
        self.cell_height = self.height / self.rows

        font_path = getattr(cfg, "FONT_PATH", "./font/JetBrainsMono-Medium.ttf")
        self.font_title = ImageFont.truetype(font_path, int(getattr(cfg, "FONT_TITLE", 15)))
        self.font_value = ImageFont.truetype(font_path, int(getattr(cfg, "FONT_VALUE", 24)))
        self.font_detail = ImageFont.truetype(font_path, int(getattr(cfg, "FONT_DETAIL", 13)))
        self.font_ring_value = ImageFont.truetype(
            font_path,
            int(getattr(cfg, "RING_VALUE_FONT", 17)),
        )
        self.font_ring_title = ImageFont.truetype(
            font_path,
            int(getattr(cfg, "RING_TITLE_FONT", 13)),
        )

    def _status_color(self, status):
        if status == "ok":
            return getattr(self.cfg, "C_OK", "#008000")
        if status == "warn":
            return getattr(self.cfg, "C_WARN", "#D08000")
        if status == "error":
            return getattr(self.cfg, "C_ERROR", "#FF0000")
        return getattr(self.cfg, "C_T1", "#000000")

    @staticmethod
    def _normalize_slot(slot):
        if isinstance(slot, str):
            return {"module": slot, "colspan": 1, "rowspan": 1}
        if isinstance(slot, dict):
            result = dict(slot)
            result.setdefault("colspan", 1)
            result.setdefault("rowspan", 1)
            return result
        return {"module": "", "colspan": 1, "rowspan": 1}

    def _slot_geometry(self, row, col, slot):
        colspan = max(1, min(int(slot.get("colspan", 1)), self.cols - col + 1))
        rowspan = max(1, min(int(slot.get("rowspan", 1)), self.rows - row + 1))
        x0 = (col - 1) * self.cell_width
        y0 = (row - 1) * self.cell_height
        x1 = x0 + self.cell_width * colspan
        y1 = y0 + self.cell_height * rowspan
        return x0, y0, x1, y1

    @staticmethod
    def _clamp_ratio(value):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _mix_color(color_a, color_b, amount):
        """Linearly interpolate between two Pillow-compatible colors."""
        amount = max(0.0, min(1.0, float(amount)))
        rgb_a = ImageColor.getrgb(color_a)
        rgb_b = ImageColor.getrgb(color_b)
        return tuple(
            int(round(a + (b - a) * amount))
            for a, b in zip(rgb_a, rgb_b)
        )

    def _ring_color(self, ratio):
        """Continuous green -> yellow -> red color scale."""
        ratio = self._clamp_ratio(ratio)
        low = getattr(self.cfg, "RING_COLOR_LOW", getattr(self.cfg, "C_OK", "#008000"))
        mid = getattr(self.cfg, "RING_COLOR_MID", "#E6C200")
        high = getattr(self.cfg, "RING_COLOR_HIGH", getattr(self.cfg, "C_ERROR", "#FF0000"))
        midpoint = self._clamp_ratio(getattr(self.cfg, "RING_COLOR_MIDPOINT", 0.60))
        midpoint = max(0.01, min(0.99, midpoint))

        if ratio <= midpoint:
            return self._mix_color(low, mid, ratio / midpoint)
        return self._mix_color(mid, high, (ratio - midpoint) / (1.0 - midpoint))

    def _resolve_ring_ratio(self, card):
        """Return (fill_ratio, color_ratio), including temperature normalization."""
        if card.get("ring_metric") == "temperature":
            raw_value = card.get("raw_value")
            if raw_value is None:
                return 0.0, None

            minimum = float(getattr(self.cfg, "TEMP_RING_MIN_C", 0.0))
            maximum = float(getattr(self.cfg, "TEMP_RING_MAX_C", 85.0))
            if maximum <= minimum:
                maximum = minimum + 1.0
            ratio = self._clamp_ratio((float(raw_value) - minimum) / (maximum - minimum))
            return ratio, ratio

        ratio = self._clamp_ratio(card.get("ratio", 0.0))
        color_ratio = card.get("color_ratio", ratio)
        if color_ratio is None:
            return ratio, None
        return ratio, self._clamp_ratio(color_ratio)

    def _draw_selection(self, draw, rect):
        x0, y0, x1, y1 = rect
        selection_color = getattr(self.cfg, "C_SELECTED", "#0066FF")
        selection_width = max(2, int(getattr(self.cfg, "SELECTED_BORDER_WIDTH", 4)))
        inset = max(1, int(getattr(self.cfg, "SELECTED_INSET", 3)))
        draw.rectangle(
            (x0 + inset, y0 + inset, x1 - inset, y1 - inset),
            outline=selection_color,
            width=selection_width,
        )

    def _draw_standard_card(self, draw, rect, card, selected=False):
        x0, y0, x1, y1 = rect
        border = getattr(self.cfg, "C_GRID", "#000000")
        bg = getattr(self.cfg, "C_CELL_BG", "#FFFFFF")
        title_color = getattr(self.cfg, "C_T2", "#777777")
        detail_color = getattr(self.cfg, "C_T2", "#777777")

        draw.rectangle((x0, y0, x1, y1), fill=bg, outline=border, width=2)

        cx = (x0 + x1) / 2
        height = y1 - y0
        title_y = y0 + height * 0.18
        value_y = y0 + height * 0.52
        detail_y = y0 + height * 0.83

        draw.text(
            (cx, title_y),
            str(card.get("title", "")),
            fill=title_color,
            font=self.font_title,
            anchor="mm",
        )
        draw.text(
            (cx, value_y),
            str(card.get("value", "")),
            fill=self._status_color(card.get("status", "normal")),
            font=self.font_value,
            anchor="mm",
        )
        detail = str(card.get("detail", ""))
        if detail:
            draw.text(
                (cx, detail_y),
                detail,
                fill=detail_color,
                font=self.font_detail,
                anchor="mm",
            )

        if selected:
            self._draw_selection(draw, rect)

    def _draw_ring_card(self, draw, rect, card, selected=False):
        """Draw a donut/ring card with the numeric value centered inside it."""
        x0, y0, x1, y1 = rect
        border = getattr(self.cfg, "C_GRID", "#000000")
        bg = getattr(self.cfg, "C_CELL_BG", "#FFFFFF")
        title_color = getattr(self.cfg, "C_T2", "#777777")
        track_color = getattr(self.cfg, "RING_TRACK_COLOR", "#D9D9D9")

        draw.rectangle((x0, y0, x1, y1), fill=bg, outline=border, width=2)

        width = x1 - x0
        height = y1 - y0
        padding = max(3, int(getattr(self.cfg, "RING_PADDING", 4)))
        title_area = max(13, int(getattr(self.cfg, "RING_TITLE_AREA", 15)))

        diameter = min(
            width - (2 * padding),
            height - title_area - (2 * padding),
        )
        diameter = max(12, diameter)

        cx = (x0 + x1) / 2
        ring_top = y0 + padding
        ring_left = cx - diameter / 2
        ring_box = (
            ring_left,
            ring_top,
            ring_left + diameter,
            ring_top + diameter,
        )

        configured_ring_width = max(2, int(getattr(self.cfg, "RING_WIDTH", 6)))
        ring_width = min(configured_ring_width, max(2, int(diameter / 4)))

        # Full neutral ring = available/free portion.
        draw.ellipse(ring_box, outline=track_color, width=ring_width)

        ratio, color_ratio = self._resolve_ring_ratio(card)
        if color_ratio is None:
            progress_color = getattr(self.cfg, "C_T2", "#777777")
            value_color = progress_color
        else:
            progress_color = self._ring_color(color_ratio)
            value_color = progress_color

        # Colored arc = used/load portion. Start at 12 o'clock.
        if ratio >= 0.999:
            draw.ellipse(ring_box, outline=progress_color, width=ring_width)
        elif ratio > 0.0:
            end_angle = -90 + (360.0 * ratio)
            draw.arc(
                ring_box,
                start=-90,
                end=end_angle,
                fill=progress_color,
                width=ring_width,
            )

        ring_cy = ring_top + diameter / 2
        draw.text(
            (cx, ring_cy),
            str(card.get("value", "")),
            fill=value_color,
            font=self.font_ring_value,
            anchor="mm",
        )

        title_y = y1 - max(7, title_area / 2)
        draw.text(
            (cx, title_y),
            str(card.get("title", "")),
            fill=title_color,
            font=self.font_ring_title,
            anchor="mm",
        )

        if selected:
            self._draw_selection(draw, rect)

    def _draw_card(self, draw, rect, card, selected=False):
        if card.get("style") == "ring":
            self._draw_ring_card(draw, rect, card, selected=selected)
            return
        self._draw_standard_card(draw, rect, card, selected=selected)

    def render_page(self, page, state, selected_key=None):
        background = getattr(self.cfg, "C_SCREEN_BG", "#FFFFFF")
        image = Image.new("RGB", (self.width, self.height), background)
        draw = ImageDraw.Draw(image)

        layout = page.get("layout", {})
        occupied = set()

        for row in range(1, self.rows + 1):
            for col in range(1, self.cols + 1):
                if (row, col) in occupied:
                    continue

                key = f"row{row}cell{col}"
                raw_slot = layout.get(key)
                if raw_slot is None:
                    self._draw_card(
                        draw,
                        self._slot_geometry(row, col, {"colspan": 1, "rowspan": 1}),
                        {"title": "", "value": "", "detail": "", "status": "normal"},
                        selected=False,
                    )
                    continue

                slot = self._normalize_slot(raw_slot)
                module_name = str(slot.get("module", "")).lower()
                builder = self.card_builders.get(module_name)
                if builder is None:
                    card = {
                        "title": "CONFIG",
                        "value": "UNKNOWN",
                        "detail": module_name or "empty",
                        "status": "error",
                    }
                    self.logger.warning("Unknown dashboard module '%s' in %s", module_name, key)
                else:
                    try:
                        card = builder(state)
                    except Exception:
                        self.logger.exception("Card builder failed: %s", module_name)
                        card = {
                            "title": module_name.upper(),
                            "value": "ERROR",
                            "detail": "renderer",
                            "status": "error",
                        }

                rect = self._slot_geometry(row, col, slot)
                self._draw_card(draw, rect, card, selected=(key == selected_key))

                colspan = int(slot.get("colspan", 1))
                rowspan = int(slot.get("rowspan", 1))
                for rr in range(row, min(self.rows, row + rowspan - 1) + 1):
                    for cc in range(col, min(self.cols, col + colspan - 1) + 1):
                        occupied.add((rr, cc))

        self.disp.ShowImage(image)
