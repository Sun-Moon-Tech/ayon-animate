"""
    Cloned from Photoshop integration
    Stub handling connection from server to client.
    Used anywhere solution is calling client methods.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import attr
from wsrpc_aiohttp import WebSocketAsync

from .webserver import WebServerTool


@attr.s
class FLAItem(object):
    """
        Object denoting layer or group item in FLA. Each item is created in
        FLA by any Loader, but contains same fields, which are being used
        in later processing.
    """
    # metadata
    id = attr.ib()  # id created by AE, could be used for querying
    name = attr.ib()  # name of item
    group = attr.ib(default=None)  # item type (footage, folder, comp)
    parents = attr.ib(factory=list)
    visible = attr.ib(default=True)
    type = attr.ib(default=None)
    # all imported elements, single for
    members = attr.ib(factory=list)
    long_name = attr.ib(default=None)
    color_code = attr.ib(default=None)  # color code of layer
    blend_mode = attr.ib(default=None)
    instance_id = attr.ib(default=None)

    @property
    def clean_name(self):
        """Returns layer name without publish icon highlight

        Returns:
            (str)
        """
        return (self.name.replace(AnimateServerStub.PUBLISH_ICON, '')
                         .replace(AnimateServerStub.LOADED_ICON, ''))


class AnimateServerStub:
    """
        Stub for calling function on client (Animate js) side.
        Expects that client is already connected (started when avalon menu
        is opened).
        'self.websocketserver.call' is used as async wrapper
    """
    PUBLISH_ICON = '\u2117 '
    LOADED_ICON = '\u25bc'
        
    @staticmethod
    def _is_evalscript_error(value):
        return isinstance(value, str) and value.strip() == "EvalScript error."

    def __init__(self):
        self.websocketserver = WebServerTool.get_instance()
        self.client = self.get_client()

    @staticmethod
    def get_client():
        """
            Return first connected client to WebSocket
            TODO implement selection by Route
        :return: <WebSocketAsync> client
        """
        clients = WebSocketAsync.get_clients()
        client = None
        if len(clients) > 0:
            key = list(clients.keys())[0]
            client = clients.get(key)

        return client

    def host_trace(self, message):
        """Helper for tracing messages in host log."""
        result = self.websocketserver.call(
            self.client.call('Animate.host_trace', message=message)
        )
        if self._is_evalscript_error(result):
            return False
        if isinstance(result, str):
            lowered = result.strip().lower()
            if lowered in {"", "null", "undefined", "false", "0"}:
                return False
        return bool(result)
    
        
    def open(self, path):
        """Open file located at 'path' (local).

        Args:
            path(string): file path locally
        Returns:
            bool: True on successful request dispatch, False otherwise.
        """
        try:
            res = self.websocketserver.call(
                self.client.call('Animate.open', path=path)
            )
        except Exception:
            return False

        if self._is_evalscript_error(res):
            return False

        if isinstance(res, str):
            lowered = res.strip().lower()
            if lowered in {"", "null", "undefined", "false", "0"}:
                return False

        return bool(res)

    def read(self, layer, layers_meta=None):
        """Parses layer metadata from Headline field of active document.

        Args:
            layer: (FLAItem)
            layers_meta: full list from Headline (for performance in loops)
        Returns:
            (dict) of layer metadata stored in FLA file

        Example:
            {
                'id': 'pyblish.avalon.container',
                'loader': 'ImageLoader',
                'members': ['64'],
                'name': 'imageMainMiddle',
                'namespace': 'Hero_imageMainMiddle_001',
                'representation': '6203dc91e80934d9f6ee7d96',
                'schema': 'openpype:container-2.0'
            }
        """
        if layers_meta is None:
            layers_meta = self.get_layers_metadata()

        for layer_meta in layers_meta:
            layer_id = layer_meta.get("uuid")  # legacy
            if layer_meta.get("members"):
                layer_id = layer_meta["members"][0]
            if str(layer.id) == str(layer_id):
                return layer_meta
        print("Unable to find layer metadata for {}".format(layer.id))

    def imprint(self, item_id, data, all_layers=None, items_meta=None):
        """Save layer metadata to Headline field of active document

        Stores metadata in format:
        [{
            "active":true,
            "productName":"imageBG",
            "productBaseType":"image",
            "id":"ayon.create.instance",
            "folderPath":"Town",
            "uuid": "8"
        }] - for created instances
        OR
        [{
            "schema": "openpype:container-2.0",
            "id": "ayon.create.instance",
            "name": "imageMG",
            "namespace": "Jungle_imageMG_001",
            "loader": "ImageLoader",
            "representation": "5fbfc0ee30a946093c6ff18a",
            "members": [
                "40"
            ]
        }] - for loaded instances

        Args:
            item_id (str):
            data(string): json representation for single layer
            all_layers (list of FLAItem): for performance, could be
                injected for usage in loop, if not, single call will be
                triggered
            items_meta(string): json representation from Headline
                           (for performance - provide only if imprint is in
                           loop - value should be same)
        Returns: None
        """
        if not items_meta:
            items_meta = self.get_layers_metadata()

        # json.dumps writes integer values in a dictionary to string, so
        # anticipating it here.
        item_id = str(item_id)
        is_new = True
        result_meta = []
        for item_meta in items_meta:
            if ((item_meta.get('members') and
                 item_id == str(item_meta.get('members')[0])) or
                    item_meta.get("instance_id") == item_id):
                is_new = False
                if data:
                    item_meta.update(data)
                    result_meta.append(item_meta)
            else:
                result_meta.append(item_meta)

        if is_new:
            result_meta.append(data)

        # Ensure only valid ids are stored.
        if not all_layers:
            all_layers = self.get_layers()
        layer_ids = [layer.id for layer in all_layers]
        cleaned_data = []

        for item in result_meta:
            if item.get("members"):
                if int(item["members"][0]) not in layer_ids:
                    continue

            cleaned_data.append(item)

        payload = json.dumps(cleaned_data, indent=4)
        self.websocketserver.call(
            self.client.call('Animate.imprint', payload=payload)
        )

    def get_layers(self):
        """Returns JSON document with all(?) layers in active document.

        Returns: <list of FLAItem>
                    Format of tuple: { 'id':'123',
                                     'name': 'My Layer 1',
                                     'type': 'GUIDE'|'FG'|'BG'|'OBJ'
                                     'visible': 'true'|'false'
        """
        res = self.websocketserver.call(
            self.client.call('Animate.get_layers')
        )

        if self._is_evalscript_error(res):
            return []
        if res is None:
            return []
        if isinstance(res, str) and res.strip().lower() in {"", "null", "undefined"}:
            return []

        return self._to_records(res)

    def get_layer(self, layer_id):
        """
            Returns FLAItem for specific 'layer_id' or None if not found
        Args:
            layer_id (string): unique layer id, stored in 'uuid' field

        Returns:
            (FLAItem) or None
        """
        layers = self.get_layers()
        for layer in layers:
            if str(layer.id) == str(layer_id):
                return layer

    def get_layers_in_layers(self, layers):
        """Return all layers that belong to layers (might be groups).

        Args:
            layers <list of FLAItem>:

        Returns:
            <list of FLAItem>
        """
        parent_ids = set([lay.id for lay in layers])

        return self._get_layers_in_layers(parent_ids)

    def get_layers_in_layers_ids(self, layers_ids, layers=None):
        """Return all layers that belong to layers (might be groups).

        Args:
            layers_ids <list of Int>
            layers <list of FLAItem>:

        Returns:
            <list of FLAItem>
        """
        parent_ids = set(layers_ids)

        return self._get_layers_in_layers(parent_ids, layers)

    def _get_layers_in_layers(self, parent_ids, layers=None):
        if not layers:
            layers = self.get_layers()

        all_layers = layers
        ret = []

        for layer in all_layers:
            parents = set(layer.parents)
            if len(parent_ids & parents) > 0:
                ret.append(layer)
            if layer.id in parent_ids:
                ret.append(layer)

        return ret

    def create_group(self, name):
        """Create new group (eg. LayerSet)

        Returns:
            <FLAItem>
        """
        enhanced_name = self.PUBLISH_ICON + name
        ret = self.websocketserver.call(
            self.client.call('Animate.create_group', name=enhanced_name)
        )
        # create group on FLA is asynchronous, returns only id
        return FLAItem(id=ret, name=name, group=True)

    def group_selected_layers(self, name):
        """Group selected layers into new LayerSet (eg. group)

        Returns:
            (Layer)
        """
        enhanced_name = self.PUBLISH_ICON + name
        res = self.websocketserver.call(
            self.client.call(
                'Animate.group_selected_layers', name=enhanced_name
            )
        )
        res = self._to_records(res)
        if res:
            rec = res.pop()
            rec.name = rec.name.replace(self.PUBLISH_ICON, '')
            return rec
        raise ValueError("No group record returned")

    def get_selected_layers(self):
        """Get a list of actually selected layers.

        Returns: <list of Layer('id':XX, 'name':"YYY")>
        """
        res = self.websocketserver.call(
            self.client.call('Animate.get_selected_layers')
        )
        return self._to_records(res)

    def select_layers(self, layers):
        """Selects specified layers in Animate by its ids.

        Args:
            layers: <list of Layer('id':XX, 'name':"YYY")>
        """
        layers_id = [str(lay.id) for lay in layers]
        self.websocketserver.call(
            self.client.call(
                'Animate.select_layers',
                layers=json.dumps(layers_id)
            )
        )

    def dissolve_layerset(self, layerset_id: str):
        """Dissolve layer set (group).

        Layers in group will be moved to parent layer set.

        Args:
            layerset_id (str): id of layer set to dissolve
        """
        self.websocketserver.call(
            self.client.call(
                'Animate.dissolve_layerset',
                layerset_id=layerset_id
            )
        )

    def merge_all_layersets(self, parent_set=None):
        """Merges layer sets into one layer.
        
        Args:
            parent_set (str): id of layer set to merge layers sets it contains.
                If None, all first level layer sets will be merged.
        """
        self.websocketserver.call(
            self.client.call(
                'Animate.merge_all_layersets',
                parent_set=parent_set,
            )
        )
    def export_png_sequence(self, path):
        """Export current document as PNG sequence to path.

        Args:
            path (str): Base path for exported frames (will append _XXXX.png)
        """
        
        result = self.websocketserver.call(
            self.client.call("Animate.export_png_sequence", path=path)
        )
        return result
        
    def export_movie(self, path):
        """Export current document as quictime mov to path.

        Args:
            path (str): Path for exported movie.
        """
        result = self.websocketserver.call(
            self.client.call("Animate.export_movie", path=path)
        )
        return result
    
    def export_swf(self, path):
        """Export current document as swf to path.

        Args:
            path (str): Path for exported swf.
        """
        result = self.websocketserver.call(
            self.client.call("Animate.export_swf", path=path)
        )
        return result

    def get_active_document_full_name(self):
        """Returns full name with path of active document via ws call

        Returns(string):
            full path with name
        """
        res = self.websocketserver.call(
            self.client.call('Animate.get_active_document_full_name')
        )
        if self._is_evalscript_error(res):
            return None
        if isinstance(res, str) and res.strip().lower() in {"", "null", "undefined"}:
            return None
        return res

    def get_active_document_name(self):
        """Returns just a name of active document via ws call

        Returns(string):
            file name
        """
        # Derive name from full path to avoid an extra fragile eval route call.
        full_name = self.get_active_document_full_name()
        if not full_name:
            return None

        return Path(str(full_name)).name or None

    def is_saved(self):
        """Returns true if no changes in active document

        Returns:
            <boolean>
        """
        res = self.websocketserver.call(
            self.client.call('Animate.is_saved')
        )
        if self._is_evalscript_error(res):
            return False
        if isinstance(res, bool):
            return res
        if isinstance(res, str):
            lowered = res.strip().lower()
            if lowered in {"true", "1"}:
                return True
            if lowered in {"false", "0", "", "null", "undefined"}:
                return False
        return bool(res)

    def save(self):
        """Saves active document"""
        self.websocketserver.call(
            self.client.call('Animate.save')
        )

    def save_workfile(self, image_path):
        """Save the active document as the current workfile at ``image_path``."""
        self.websocketserver.call(
            self.client.call(
                'Animate.save_workfile',
                path=image_path,
            )
        )

    def save_copy(self, image_path):
        """Save a copy of the active document to ``image_path``."""
        self.websocketserver.call(
            self.client.call(
                'Animate.save_copy',
                path=image_path,
            )
        )

    def saveAs(self, image_path, ext, as_copy):
        """Compatibility wrapper for legacy Animate saveAs calls.

        Args:
            image_path(string): full local path
            ext: file extension, typically ``fla`` for workfiles
            as_copy: <boolean>
        Returns: None
        """
        if as_copy:
            return self.save_copy(image_path)
        return self.save_workfile(image_path)

    @contextmanager
    def duplicate_document(self, path: str):
        """Duplicate active document and save it to path.

        Can be used as context manager:

            with Animate.duplicate_document(path):
                # do Animate things with duplicated document
                pass

        Args:
            path (str): file path to save duplicated document
        """
        try:
            path = Path(path)
            document_id = self.websocketserver.call(
                self.client.call(
                    'Animate.duplicate_document',
                    newName=path.name,
                )
            )
            yield
        finally:
            # Save and close the duplicated document
            self.save_copy(str(path))
            self.close_document(document_id)

    def close_document(self, id: str):
        """Close document with id."""
        self.websocketserver.call(
            self.client.call(
                'Animate.close_document',
                id=id
            )
        )

    def revert_to_previous(self):
        """Reverts active document to last saved state"""
        self.websocketserver.call(
            self.client.call('Animate.revert_to_previous')
        )

    def set_visible(self, layer_id, visibility):
        """Set layer with 'layer_id' to 'visibility'

        Args:
            layer_id: <int>
            visibility: <true - set visible, false - hide>
        Returns: None
        """
        self.websocketserver.call(
            self.client.call(
                'Animate.set_visible',
                layer_id=layer_id,
                visibility=visibility
            )
        )

    def set_layers_visibility(self, visibility_map: dict[int, bool]):
        """Set visibility for multiple layers in one call.

        Args:
            visibility_map (dict[int, bool]): {layer_id: bool, ...}
        """
        self.websocketserver.call(
            self.client.call(
                'Animate.set_layers_visibility',
                visibility_map=json.dumps(visibility_map)
            )
        )

    def delete_all_layers(self, exclude_layers=None, exclude_recursive=False):
        """Delete all layers except the ones in the exclude_layers list.

        Args:
            exclude_layers (list): list of layer ids to exclude from deletion
            exclude_recursive (bool): layersets within exclude_layers will also be excluded
        """
        exclude_ids = {layer.id for layer in exclude_layers}
        if exclude_recursive:
            exclude_ids |= {ll.id for ll in self.get_layers_in_layers(exclude_layers)}
        
        for layer in self.get_layers():
            if layer.id not in exclude_ids:
                self.delete_layer(layer.id)

    def get_layers_metadata(self):
        """Reads layers metadata from Headline from active document in FLA.
        (Headline accessible by File > File Info)

        Returns:
            (list)
            example:
                {"8":{"active":true,"productName":"imageBG",
                      "productBaseType":"image","id":"ayon.create.instance",
                      "folderPath":"/Town"}}
                8 is layer(group) id - used for deletion, update etc.
        """
        res = self.websocketserver.call(self.client.call('Animate.read'))
        if self._is_evalscript_error(res):
            return []
        layers_data = []
        if isinstance(res, str) and res.strip().lower() in {"", "null", "undefined"}:
            return layers_data
        try:
            if res:
                layers_data = json.loads(res)
        except json.decoder.JSONDecodeError:
            print("{} cannot be parsed, returning empty metadata".format(res))
            return []
        # format of metadata changed from {} to [] because of standardization
        # keep current implementation logic as its working
        if isinstance(layers_data, dict):
            for layer_id, layer_meta in layers_data.items():
                if layer_meta.get("schema") != "openpype:container-2.0":
                    layer_meta["members"] = [str(layer_id)]
            layers_data = list(layers_data.values())
        return layers_data

    def import_smart_object(self, path, layer_name, as_reference=False):
        """Import the file at `path` as a smart object to active document.

        Args:
            path (str): File path to import.
            layer_name (str): Unique layer name to differentiate how many times
                same smart object was loaded
            as_reference (bool): pull in content or reference
        """
        enhanced_name = self.LOADED_ICON + layer_name
        res = self.websocketserver.call(
            self.client.call(
                'Animate.import_smart_object',
                path=path,
                name=enhanced_name,
                as_reference=as_reference
            )
        )
        rec = self._to_records(res).pop()
        if rec:
            rec.name = rec.name.replace(self.LOADED_ICON, '')
        return rec

    def replace_smart_object(self, layer, path, layer_name):
        """Replace the smart object `layer` with file at `path`

        Args:
            layer (FLAItem):
            path (str): File to import.
            layer_name (str): Unique layer name to differentiate how many times
                same smart object was loaded
        """
        enhanced_name = self.LOADED_ICON + layer_name
        self.websocketserver.call(
            self.client.call(
                'Animate.replace_smart_object',
                layer_id=layer.id,
                path=path,
                name=enhanced_name
            )
        )

    def delete_layer(self, layer_id):
        """Deletes specific layer by it's id.

        Args:
            layer_id (int): id of layer to delete
        """
        self.websocketserver.call(
            self.client.call('Animate.delete_layer', layer_id=layer_id)
        )

    def rename_layer(self, layer_id, name):
        """Renames specific layer by it's id.

        Args:
            layer_id (int): id of layer to delete
            name (str): new name
        """
        self.websocketserver.call(
            self.client.call(
                'Animate.rename_layer',
                layer_id=layer_id,
                name=name
            )
        )

    def get_color_profile_name(self):
        """Returns active document's color profile name."""
        colorspace_profile = self.websocketserver.call(
            self.client.call('Animate.get_color_profile_name')
        )
        return colorspace_profile

    def remove_instance(self, instance_id):
        cleaned_data = []

        for item in self.get_layers_metadata():
            inst_id = item.get("instance_id") or item.get("uuid")
            if inst_id != instance_id:
                cleaned_data.append(item)

        payload = json.dumps(cleaned_data, indent=4)

        self.websocketserver.call(
            self.client.call('Animate.imprint', payload=payload)
        )

    def get_extension_version(self):
        """Returns version number of installed extension."""
        return self.websocketserver.call(
            self.client.call('Animate.get_extension_version')
        )

    def get_layer_blend_mode(self, layer_id):
        """Returns blend mode string for specific layer."""
        return self.websocketserver.call(
            self.client.call('Animate.get_layer_blend_mode', layer_id=layer_id)
        )

    def get_document_settings(self):
        """Returns dict with document resolution, mode and bits per channel."""
        res = self.websocketserver.call(
            self.client.call('Animate.get_document_settings')
        )
        if not res:
            return {}
        try:
            return json.loads(res)
        except json.decoder.JSONDecodeError:
            raise ValueError("Received broken JSON {}".format(res))

    def set_document_settings(self, resolution=None, mode=None, bits=None):
        """Sets document resolution, color mode, and/or bit depth.

        Args:
            resolution (int, optional): Target DPI.
            mode (str, optional): Target color mode (RGB, CMYK, GRAYSCALE, etc.)
            bits (int or str, optional): Target bit depth (8, 16, or 32).

        Returns:
            dict: Result with 'success' key and optional 'errors' list.

        Note:
            Some conversions may be lossy (e.g., CMYK to RGB, 32 to 16 bits).
        """
        res = self.websocketserver.call(
            self.client.call(
                'Animate.set_document_settings',
                resolution=resolution,
                mode=mode,
                bits=bits
            )
        )
        if not res:
            return {"success": False, "error": "No response from Animate"}
        try:
            return json.loads(res)
        except json.decoder.JSONDecodeError:
            raise ValueError("Received broken JSON {}".format(res))

    def close(self):
        """Shutting down FLA and process too.

            For webpublishing only.
        """
        # TODO change client.call to method with checks for client
        self.websocketserver.call(self.client.call('Animate.close'))

    def eval(self, code: str):
        """Execute Javascript code.

        Args:
            code (str): Javascript code to execute.

        Returns:
            Any: Result of javascript execution.

        """
        # TODO: Can we provide more info to the user on execution failure
        #  on the javascript side, like raising an informative error?
        return self.websocketserver.call(
            self.client.call(
                'Animate.eval_code',
                code=code,
            )
        )

    def _to_records(self, res):
        """Converts string json representation into list of FLAItem for
        dot notation access to work.

        Args:
            res (string): valid json

        Returns:
            <list of FLAItem>
        """
        if res is None:
            return []

        if self._is_evalscript_error(res):
            return []

        if isinstance(res, str):
            normalized = res.strip().lower()
            if normalized in {"", "null", "undefined"}:
                return []

        # Some websocket paths may already return decoded objects.
        if isinstance(res, (list, dict)):
            layers_data = res
        else:
            try:
                layers_data = json.loads(res)
            except (json.decoder.JSONDecodeError, TypeError):
                raise ValueError("Received broken JSON {}".format(res))

        ret = []

        # convert to AEItem to use dot donation
        if isinstance(layers_data, dict):
            layers_data = [layers_data]
        for d in layers_data:
            # currently implemented and expected fields
            ret.append(FLAItem(
                d.get('id'),
                d.get('name'),
                d.get('group'),
                d.get('parents'),
                d.get('visible'),
                d.get('type'),
                d.get('members'),
                d.get('long_name'),
                d.get("color_code"),
                d.get("blend_mode"),
                d.get("instance_id")
            ))
        return ret
