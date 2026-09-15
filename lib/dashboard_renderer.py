"""Layout and card rendering for the modular dashboard."""

from PIL import Image, ImageColor, ImageDraw, ImageFont


class DashboardRenderer:
    def __init__(self, disp, cfg, card_builders, logger):
        self.disp = disp
        self.cfg = cfg
        self.card_builders = card_builders
        self.logger = logger

        # All currently supported LCD drivers expose native portrait dimensions.
        # The dashboard is rendered in landscape, so width/height are swapped.
        # This makes the logical matrix automatically follow the selected LCD's
        # actual resolution (e.g. 320x240 or 280x240).
        self.width = int(disp.height)
        self.height = int(disp.width)
        self.rows = max(1, int(getattr(cfg, "GRID_ROWS", 3)))
        self.cols = max(1, int(getattr(cfg, "GRID_COLS", 3)))
        self.cell_width = self.width / self.cols
        self.cell_height = self.height / self.rows

        self.font_path = getattr(cfg, "FONT_PATH", "./font/JetBrainsMono-Medium.ttf")
        self.font_cache = {}

        reference_width = max(1, int(getattr(cfg, "FONT_REFERENCE_WIDTH", 320)))
        reference_height = max(1, int(getattr(cfg, "FONT_REFERENCE_HEIGHT", 240)))
        if bool(getattr(cfg, "AUTO_FONT_SCALE", True)):
            self.font_scale = min(
                self.width / reference_width,
                self.height / reference_height,
            )
            self.font_scale = max(
                float(getattr(cfg, "FONT_SCALE_MIN", 0.60)),
                min(float(getattr(cfg, "FONT_SCALE_MAX", 1.50)), self.font_scale),
            )
        else:
            self.font_scale = 1.0

        self.logger.info(
            "Renderer canvas=%dx%d grid=%dx%d cell=%.1fx%.1f font_scale=%.3f",
            self.width,
            self.height,
            self.rows,
            self.cols,
            self.cell_width,
            self.cell_height,
            self.font_scale,
        )

    def _font(self, size):
        size = max(1, int(round(size)))
        font = self.font_cache.get(size)
        if font is None:
            font = ImageFont.truetype(self.font_path, size)
            self.font_cache[size] = font
        return font

    def _scaled_font_size(self, config_name, default):
        configured = max(1, int(getattr(self.cfg, config_name, default)))
        return max(1, int(round(configured * self.font_scale)))

    @staticmethod
    def _text_size(draw, text, font):
        if not text:
            return 0, 0
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top

    def _fit_font(self, draw, text, max_size, min_size, max_width, max_height=None):
        """Return the largest cached font that fits the available rectangle."""
        text = str(text or "")
        max_size = max(1, int(round(max_size)))
        min_size = max(1, min(int(round(min_size)), max_size))
        max_width = max(1.0, float(max_width))
        max_height = None if max_height is None else max(1.0, float(max_height))

        if not text:
            return self._font(max_size)

        for size in range(max_size, min_size - 1, -1):
            font = self._font(size)
            text_width, text_height = self._text_size(draw, text, font)
            if text_width <= max_width and (
                max_height is None or text_height <= max_height
            ):
                return font

        return self._font(min_size)

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

        width = x1 - x0
        height = y1 - y0
        cx = (x0 + x1) / 2
        title_y = y0 + height * 0.18
        value_y = y0 + height * 0.52
        detail_y = y0 + height * 0.83

        text_padding = max(
            2,
            int(round(float(getattr(self.cfg, "TEXT_HORIZONTAL_PADDING", 5)) * self.font_scale)),
        )
        available_width = max(1, width - (2 * text_padding))

        title = str(card.get("title", ""))
        value = str(card.get("value", ""))
        detail = str(card.get("detail", ""))

        title_font = self._fit_font(
            draw,
            title,
            self._scaled_font_size("FONT_TITLE", 15),
            int(getattr(self.cfg, "FONT_MIN_TITLE", 8)),
            available_width,
            height * 0.22,
        )
        value_font = self._fit_font(
            draw,
            value,
            self._scaled_font_size("FONT_VALUE", 24),
            int(getattr(self.cfg, "FONT_MIN_VALUE", 10)),
            available_width,
            height * 0.34,
        )
        detail_font = self._fit_font(
            draw,
            detail,
            self._scaled_font_size("FONT_DETAIL", 13),
            int(getattr(self.cfg, "FONT_MIN_DETAIL", 7)),
            available_width,
            height * 0.22,
        )

        draw.text(
            (cx, title_y),
            title,
            fill=title_color,
            font=title_font,
            anchor="mm",
        )
        draw.text(
            (cx, value_y),
            value,
            fill=self._status_color(card.get("status", "normal")),
            font=value_font,
            anchor="mm",
        )
        if detail:
            draw.text(
                (cx, detail_y),
                detail,
                fill=detail_color,
                font=detail_font,
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
        padding = max(3, int(round(float(getattr(self.cfg, "RING_PADDING", 4)) * self.font_scale)))
        title_area = max(11, int(round(float(getattr(self.cfg, "RING_TITLE_AREA", 15)) * self.font_scale)))

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

        configured_ring_width = max(
            2,
            int(round(float(getattr(self.cfg, "RING_WIDTH", 6)) * self.font_scale)),
        )
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

        value = str(card.get("value", ""))
        title = str(card.get("title", ""))
        inner_diameter = max(8, diameter - (2 * ring_width) - 4)

        ring_value_font = self._fit_font(
            draw,
            value,
            self._scaled_font_size("RING_VALUE_FONT", 17),
            int(getattr(self.cfg, "FONT_MIN_RING_VALUE", 8)),
            inner_diameter,
            inner_diameter * 0.55,
        )
        ring_title_font = self._fit_font(
            draw,
            title,
            self._scaled_font_size("RING_TITLE_FONT", 13),
            int(getattr(self.cfg, "FONT_MIN_RING_TITLE", 7)),
            max(1, width - (2 * padding)),
            title_area,
        )

        ring_cy = ring_top + diameter / 2
        draw.text(
            (cx, ring_cy),
            value,
            fill=value_color,
            font=ring_value_font,
            anchor="mm",
        )

        title_y = y1 - max(6, title_area / 2)
        draw.text(
            (cx, title_y),
            title,
            fill=title_color,
            font=ring_title_font,
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
