"""Icon generator — draws color-coded circular tray icons at runtime."""

from enum import Enum

from PIL import Image, ImageDraw


class TrayColor(Enum):
    GREEN = (0, 200, 80)     # < 50% used — healthy
    YELLOW = (255, 200, 0)   # 50–80% used — warning
    RED = (255, 60, 60)      # > 80% used — critical
    GRAY = (150, 150, 150)   # Disconnected / no data / error


class IconGenerator:
    """Generates color-coded circular tray icons in memory.

    Draws at 64×64 for anti-aliasing; Windows scales down to 16×16
    in the notification area.
    """

    SIZE = 64          # Canvas dimensions (square)
    RADIUS = 26        # Circle radius
    CENTER = (32, 32)  # Center of the canvas
    BORDER_WIDTH = 2   # White border around the circle

    @staticmethod
    def generate(color: TrayColor) -> Image.Image:
        """Create a filled-circle icon of the given color on a transparent background.

        Args:
            color: TrayColor enum value determining the fill color.

        Returns:
            PIL Image in RGBA mode, suitable for pystray.Icon.
        """
        img = Image.new("RGBA", (IconGenerator.SIZE, IconGenerator.SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Outer border (slightly larger)
        outer_bbox = [
            IconGenerator.CENTER[0] - IconGenerator.RADIUS - IconGenerator.BORDER_WIDTH,
            IconGenerator.CENTER[1] - IconGenerator.RADIUS - IconGenerator.BORDER_WIDTH,
            IconGenerator.CENTER[0] + IconGenerator.RADIUS + IconGenerator.BORDER_WIDTH,
            IconGenerator.CENTER[1] + IconGenerator.RADIUS + IconGenerator.BORDER_WIDTH,
        ]
        draw.ellipse(outer_bbox, fill=(255, 255, 255, 255))

        # Inner filled circle
        inner_bbox = [
            IconGenerator.CENTER[0] - IconGenerator.RADIUS,
            IconGenerator.CENTER[1] - IconGenerator.RADIUS,
            IconGenerator.CENTER[0] + IconGenerator.RADIUS,
            IconGenerator.CENTER[1] + IconGenerator.RADIUS,
        ]
        draw.ellipse(inner_bbox, fill=color.value)

        return img

    @staticmethod
    def color_for_usage(usage_pct: float) -> TrayColor:
        """Map usage percentage to the appropriate tray color.

        Args:
            usage_pct: Percentage of budget used (0–100+).

        Returns:
            GREEN if < 50%, YELLOW if 50–80%, RED if > 80%.
        """
        if usage_pct < 50:
            return TrayColor.GREEN
        elif usage_pct < 80:
            return TrayColor.YELLOW
        else:
            return TrayColor.RED
