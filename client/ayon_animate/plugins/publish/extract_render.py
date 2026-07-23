import subprocess
import os
from pathlib import Path
from ayon_core.lib.vendor_bin_utils import get_ffmpeg_tool_args


import pyblish.api
from ayon_core.pipeline import publish
from ayon_animate import api as animate


class ExtractRender(pyblish.api.InstancePlugin):
    """Export render instances.

    Exports visible to a mov or png seq.
    
    """

    order = publish.Extractor.order - 0.48
    label = "Extract Render"
    hosts = ["animate"]

    families = ["render"]
    settings_category = "animate"

    def host_trace(self, message):
        return animate.stub().host_trace(message)
 
    def process(self, instance):
        """Extract render instance and output an mp4 representation"""
        self.log.info(f"Extracting render: {instance.data['name']}")
        
        stub = animate.stub()
        staging_dir = self.staging_dir(instance)
        
        doc_name = stub.get_active_document_name()
        if not doc_name:
            raise RuntimeError("No active Animate document")
        
        file_basename = Path(doc_name).stem
        instance_name = instance.data["name"]
        task_type = instance.data.get("task")
        output_basename = f"{file_basename}_{instance_name}"
        output_path = os.path.join(staging_dir, output_basename)

        ## hard-coded defaults, which should then be set below
        is_swf_task = False
        render_source = "movie"

        ## attempt to integrate task_specific render profiles
        render_profile = self._get_render_profile( task_type )
        if render_profile:
            is_swf_task = render_profile["export_swf"]
            render_source = render_profile["render_source"]
        else:
            self.log.info( "Getting default publish settings" )
            ## default settings
            if not getattr(self, "swf_tasks", None):
                self.log.warning("No SWF tasks specified in settings")
                is_swf_task = False
            else:
                self.log.info( f"swf_tasks found: {self.swf_tasks}" )
                is_swf_task = self._get_swf_settings( task_type, self.swf_tasks )
            
            ## check for default render source
            render_source = getattr(self, "render_source", None)
            if not render_source:
                self.log.warning(f"No render source specified, defaulting to '{render_source}'")

        self.log.info(f"Export SWF: {is_swf_task}" )
        self.log.info(f"Render source mode: {render_source}" )

        if render_source == "png_sequence":
            self.log.info(f"Exporting PNG sequence to {staging_dir}")
            self._export_png_sequence(output_path)

            frame_files = self._collect_exported_frames(staging_dir, output_basename)
            if not frame_files:
                raise RuntimeError(
                    f"No PNG frames exported to {staging_dir}"
                )

            self.log.info(f"Exported {len(frame_files)} frames")
            mp4_output = self._convert_sequence_to_mp4(staging_dir, output_basename)
            self.log.info(f"Converted PNG sequence to MP4: {mp4_output}")
        else:
            self.log.info(f"Exporting mov to {staging_dir}")
            movie = self.export_movie(output_path)
            video_output = self._adjust_mov_paths(movie, staging_dir, output_basename)

            if render_source == "h264":
                mp4_output = self._convert_movie_to_mp4(
                    video_output,
                    staging_dir,
                    output_basename,
                )
                self.log.info(f"Converted QuickTime movie to MP4: {mp4_output}")
                ## placeholder, really lazy way to remove the mov to save space
                self.clean_up_mov(
                    video_output,
                    staging_dir,
                    output_basename,
                )
        swf_output = None

        if is_swf_task:
            swf_output = self.export_swf(output_path)
            self.log.info(f"Exported SWF: {swf_output}")

        frame_start = instance.data.get("frameStart", 0)
        frame_end = instance.data.get("frameEnd", 1)
        
        # This is where we define the representations for the extracted media. Can change this to include the mp4 option instead or as well. 
        if render_source == "movie":
            representation = {
                "name": "mov",
                "ext": "mov",
                "files": video_output,
                "stagingDir": staging_dir,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "fps": instance.data.get("fps", 25),
                "tags": ["review"],
            }
        else:
            representation = {
                "name": "mp4",
                "ext": "mp4",
                "files": mp4_output,
                "stagingDir": staging_dir,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "fps": instance.data.get("fps", 25),
                "tags": ["review"],
            }
        instance.data["representations"].append(representation)

        if swf_output:
            swf_representation = {
                "name": "swf",
                "ext": "swf",
                "files": swf_output,
                "stagingDir": staging_dir,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "fps": instance.data.get("fps", 25),
                "tags": [],
            }
            instance.data["representations"].append(swf_representation)
        
        instance.data["stagingDir"] = staging_dir
        
        self.log.info(f"Extracted {instance.data['name']} to {staging_dir}")

    def _get_render_profile(self,task_type):
        if getattr(self,"task_render_profiles",None):
            for render_profile in self.task_render_profiles:
                self.log.info( "Checking render profile: " + str(render_profile) )
                if task_type in [t.lower() for t in render_profile["task_types"]]:
                    self.log.info( "Render profile found in " + str(render_profile["task_types"]) )
                    return render_profile
            self.log.info( f"Task type '{task_type}' does not match any render profiles" )
        else:
            self.log.info( "No render profiles defined in project settings")
        return None

    def _get_swf_settings(self,task_type,swf_tasks):
        if task_type in [task.lower() for task in swf_tasks]:
            self.log.info( f"Task type '{task_type}' will require a SWF export")
            return True
        return False

    def _export_png_sequence(self,output_path):
        export_path = str(output_path).replace("\\", "/")
        
        result = animate.stub().export_png_sequence(export_path)
        if not result or result is False:
            raise RuntimeError("Failed to export PNG sequence from Animate")

    def export_movie(self, output_path):
        export_path = str(output_path).replace("\\", "/")
        include_alpha = getattr(self,"include_alpha_in_mov",False)
        return animate.stub().export_movie(export_path,include_alpha)

    def export_swf(self, output_path):
        export_path = str(output_path).replace("\\", "/")
        result = animate.stub().export_swf(export_path)
        swf_path = self._resolve_exported_media_path(
            result,
            staging_dir=os.path.dirname(output_path),
            basename=os.path.basename(output_path),
            extension="swf",
        )
        return os.path.basename(swf_path)

    def _collect_exported_frames(self, staging_dir, basename):
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
    
    def _convert_sequence_to_mp4(self, staging_dir, basename):
        """Convert exported PNG sequence to MP4 using ffmpeg"""
        mp4_path = os.path.join(staging_dir, f"{basename}.mp4")

        png_pattern = os.path.join(staging_dir, f"{basename}%04d.png")
        args = [
            "-y",
            "-framerate",
            "25",
            "-i",
            png_pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            mp4_path,
        ]

        self._run_ffmpeg(args)
        return os.path.basename(mp4_path)
        
    def _adjust_mov_paths(self, movie_output, staging_dir, basename):
        mov_path = os.path.join(staging_dir, f"{basename}.mov")
        if not os.path.exists(mov_path):
            raise RuntimeError(f"Exported QuickTime movie not found: {mov_path}")
        return os.path.basename(mov_path)
    
    def _convert_movie_to_mp4(self, movie_output, staging_dir, basename):
        movie_path = self._resolve_exported_media_path(
            movie_output,
            staging_dir=staging_dir,
            basename=basename,
            extension="mov",
        )

        mp4_path = os.path.join(staging_dir, f"{basename}.mp4")
        args = [
            "-y",
            "-i",
            movie_path,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            mp4_path,
        ]

        self._run_ffmpeg(args)
        return os.path.basename(mp4_path)

    def _run_ffmpeg(self, args):
        ffmpeg = get_ffmpeg_tool_args("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("Failed to find ffmpeg executable")

        arg_list = ffmpeg + args
        self.log.info(f"Running ffmpeg command: {subprocess.list2cmdline(arg_list)}")

        proc = subprocess.Popen(
            arg_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, stderr = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed (exit {proc.returncode}):\n"
                + stderr.decode("utf-8", errors="replace")
            )

    def _resolve_exported_media_path(self, export_result, staging_dir, basename, extension):
        if isinstance(export_result, str):
            normalized = export_result.strip()
            lowered = normalized.lower()

            # Host side may return boolean values as strings.
            if lowered in {"true", "1"}:
                export_path = os.path.join(staging_dir, f"{basename}.{extension}")
            elif lowered in {"false", "0", "", "null", "undefined"}:
                raise RuntimeError(
                    f"Animate export failed for '{basename}.{extension}'"
                )
            else:
                if lowered.startswith("file:///"):
                    normalized = normalized[8:]
                normalized = normalized.replace("/", os.path.sep)
                if os.path.isabs(normalized):
                    export_path = normalized
                else:
                    export_path = os.path.join(staging_dir, normalized)
        elif export_result:
            export_path = os.path.join(staging_dir, f"{basename}.{extension}")
        else:
            raise RuntimeError(
                f"Animate export failed for '{basename}.{extension}'"
            )

        if not os.path.exists(export_path):
            raise RuntimeError(f"Exported file not found: {export_path}")

        return export_path   
    
    def clean_up_mov( self, movie_output, staging_dir, basename ):
        movie_path = self._resolve_exported_media_path(
            movie_output,
            staging_dir=staging_dir,
            basename=basename,
            extension="mov",
        )

        if os.path.exists( movie_path ):
            try:
                os.remove( movie_path )
                self.log.info( f"Removed QuickTime movie from staging path" )
            except:
                self.log.warning( f"Could not remove QuickTime movie at '{movie_path}'. Publish script will continue")
        else:
            self.log.warning( f"Could not find QuickTime movie at '{movie_path}'")


    def staging_dir(self, instance):
        from ayon_core.pipeline.publish import get_instance_staging_dir
        return get_instance_staging_dir(instance)
