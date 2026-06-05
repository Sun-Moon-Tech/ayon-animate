import subprocess
import os
from pathlib import Path
from ayon_core.lib.vendor_bin_utils import get_ffmpeg_tool_args


import pyblish.api
from ayon_core.pipeline import publish
from ayon_animate import api as animate


class ExtractRender(pyblish.api.InstancePlugin):
    """Export render instances as PNG image sequences.

    Exports the visible layers to a PNG sequence file in the staging
    directory for each render instance.
    """

    order = publish.Extractor.order - 0.48
    label = "Extract Render"
    hosts = ["animate"]

    families = ["render"]
    settings_category = "animate"
    def host_trace(self, message):
        return animate.stub().host_trace(message)
 
    def process(self, instance):
        """Extract PNG sequence for render instance."""
        self.log.info(f"Extracting render: {instance.data['name']}")
        
        stub = animate.stub()
        staging_dir = self.staging_dir(instance)
        
        # Get document name for output filename
        doc_name = stub.get_active_document_name()
        if not doc_name:
            raise RuntimeError("No active Animate document")
        
        # Build output path for PNG sequence (without frame number)
        # Animate will append frame numbers like _0000.png, _0001.png, etc.
        file_basename = Path(doc_name).stem
        instance_name = instance.data["name"]
        output_basename = f"{file_basename}_{instance_name}"
        output_path = os.path.join(staging_dir, output_basename)
        
        # Export PNG sequence
        self.log.info(f"Exporting PNG sequence to {staging_dir}")
        self._export_png_sequence(output_path)
        
        # Find all exported frame files to create representation
        frame_files = self._collect_exported_frames(staging_dir, output_basename)
        if not frame_files:
            raise RuntimeError(
                f"No PNG frames exported to {staging_dir}"
            )
    
        self.log.info(f"Exported {len(frame_files)} frames")

        mp4_output = self._convert_to_mp4(frame_files, staging_dir, output_basename)  

        self.log.info(f"Converted PNG sequence to MP4: {mp4_output}")  
        # Create representation
        representation = {
            "name": "mp4",
            "ext": "mp4",
            "files": mp4_output,
            "stagingDir": staging_dir,
            "frameStart": 0,
            "frameEnd": len(frame_files) - 1,
            "fps": 25,
            "tags": ["review"],
        }
         
        instance.data["representations"] = [representation]
        instance.data["stagingDir"] = staging_dir
        
        self.log.info(f"Extracted {instance.data['name']} to {staging_dir}")

    def _export_png_sequence(self,output_path):
        """Export current document as PNG sequence.
        
        Args:
            stub: Animate API stub
            output_path: Base path for exported frames (will append _XXXX.png)
        """
        # Convert path to use forward slashes for JSX
        export_path = str(output_path).replace("\\", "/")
        
        result = animate.stub().export_png_sequence(export_path)
        if not result or result is False:
            raise RuntimeError("Failed to export PNG sequence from Animate")

    def _collect_exported_frames(self, staging_dir, basename):
        """Collect all exported PNG frame files.
        
        Args:
            staging_dir: Directory containing exported frames
            basename: Base filename without frame numbers
            
        Returns:
            List of frame filenames sorted by frame number
        """
        import glob
        self.host_trace("basename: " + basename + " staging_dir: " + staging_dir)
        pattern = os.path.join(staging_dir, f"{basename}*.png")
        files = sorted(glob.glob(pattern))
        self.host_trace(f"pattern: {pattern}")
        if not files:
            self.host_trace(f"No frames found matching pattern: {pattern}")
            return []
        
        # Extract just filenames
        return [os.path.basename(f) for f in files]
    
    def _convert_to_mp4(self, frames, staging_dir, basename):
        """Convert exported PNG sequence to MP4 using ffmpeg."""
        if not frames:
            raise RuntimeError("No PNG frames to convert to MP4")
        mp4_path = os.path.join(staging_dir, f"{basename}.mp4")
        
        # Build ffmpeg command
        png_pattern = os.path.join(staging_dir, f"{basename}%04d.png")
        args = ["-y", "-framerate", "25", "-i", png_pattern, "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4_path]

        ffmpeg = get_ffmpeg_tool_args("ffmpeg")

        if not ffmpeg:
            raise RuntimeError("Failed to find ffmpeg executable")
        arg_list = ffmpeg + args
        cmd = " ".join(arg_list)        
        self.log.info(f"Running ffmpeg command: {cmd}")

        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if not proc:
            raise RuntimeError("Failed to start ffmpeg process")   
        
        return os.path.basename(mp4_path)
    
    def staging_dir(self, instance):
        """Provide staging directory for extracted files."""
        from ayon_core.pipeline.publish import get_instance_staging_dir
        return get_instance_staging_dir(instance)
