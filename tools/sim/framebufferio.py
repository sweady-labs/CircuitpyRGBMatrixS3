"""Stand-in for framebufferio: refresh() renders the group tree into self.picture."""
import displayio


class FramebufferDisplay:
    def __init__(self, framebuffer, *, auto_refresh=True, rotation=0):
        self.framebuffer = framebuffer
        self.width = framebuffer.width
        self.height = framebuffer.height
        self.auto_refresh = auto_refresh
        self.root_group = None
        self.picture = None

    def refresh(self, *, target_frames_per_second=None, minimum_frames_per_second=0):
        self.picture = displayio.render(self.root_group, self.width, self.height)
        return True
