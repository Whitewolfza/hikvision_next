"""Component providing support for Hikvision IP cameras."""

from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from . import HikvisionConfigEntry
from .hikvision_device import HikvisionDevice
from .isapi import AnalogCamera, CameraStreamInfo, IPCamera


async def async_setup_entry(
    hass: HomeAssistant, entry: HikvisionConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a Hikvision IP Camera."""

    device = entry.runtime_data

    entities = []
    for camera in device.cameras:
        for stream in camera.streams:
            entities.append(HikvisionCamera(device, camera, stream))

    async_add_entities(entities)


class HikvisionCamera(Camera):
    """An implementation of a Hikvision IP camera."""

    _attr_supported_features: CameraEntityFeature = CameraEntityFeature.STREAM

    def __init__(
        self,
        device: HikvisionDevice,
        camera: AnalogCamera | IPCamera,
        stream_info: CameraStreamInfo,
    ) -> None:
        """Initialize Hikvision camera stream."""
        Camera.__init__(self)

        self._attr_device_info = device.hass_device_info(camera.id)
        self._attr_unique_id = slugify(f"{device.device_info.serial_no.lower()}_{stream_info.id}")
        if stream_info.type_id > 1:
            self._attr_has_entity_name = True
            self._attr_translation_key = f"stream{stream_info.type_id}"
            self._attr_entity_registry_enabled_default = False
        else:
            # for the main stream use just its name
            self._attr_name = camera.name
        self.entity_id = f"camera.{self.unique_id}"
        self.device = device
        self.camera = camera
        self.streams = camera.streams
        self.stream_info = stream_info
        self._selected_stream_type_id = stream_info.type_id

    @property
    def extra_state_attributes(self):
        return {
            "available_stream_types": [s.type for s in self.streams],
            "selected_stream_type": self.stream_info.type,
        }

    async def async_set_stream_type(self, stream_type: str):
        """Set the stream type (main, sub, extra) for the camera."""
        for s in self.streams:
            if s.type == stream_type:
                self.stream_info = s
                self._selected_stream_type_id = s.type_id
                await self.async_update_ha_state()
                return
        raise ValueError(f"Stream type '{stream_type}' not found.")

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        return self.device.get_stream_source(self.stream_info)

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return a still image response from the camera."""
        return await self.device.get_camera_image(self.stream_info, width, height)
