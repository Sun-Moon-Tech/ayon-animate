import subprocess
import os, json
from pathlib import Path
from ayon_core.lib.vendor_bin_utils import get_ffmpeg_tool_args


import pyblish.api
import ayon_api
from ayon_core.pipeline import (
    publish,
    Anatomy
)
from ayon_core.pipeline.template_data import get_template_data
from ayon_core.lib import path_tools
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

    creator_attributes = None
    render_source = "mp4"
    pip_settings = None

    frame_start = 0
    frame_end = 0
    fps = 0
    timeline_end = 0

    def host_trace(self, message):
        return animate.stub().host_trace(message)
 
    def process(self, instance):
        """Extract render instance and output an mp4 representation"""
        self.log.info(f"Extracting render: {instance.data['name']}")

        self.creator_attributes = instance.data.get("creator_attributes")
        if "renderSource" in instance.data:
            self.render_source = instance.data.get("renderSource")

        self.frame_start = instance.data.get("frameStart", 0) if not ("start_frame" in self.creator_attributes) else self.creator_attributes["start_frame"]
        self.frame_end = instance.data.get("frameEnd", 1) if not ("end_frame" in self.creator_attributes) else self.creator_attributes["end_frame"]
        self.fps =  instance.data.get("fps", 25)
        timeline_end = instance.data.get("timelineLength",self.frame_end)

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

        ## attempt to get picture-in-picture working
        pip_file_path = None
        if "include_reference_pip" in self.creator_attributes:
            if self.creator_attributes["include_reference_pip"]:
                self.pip_settings = getattr(self,"picture_in_picture",None)
                pip_file_path = self._get_pip_entity(instance)
                if not pip_file_path:
                    self.log.warning(f"A reference picture-in-picture was requested, but no suitable file was found.")
                else:
                    self.log.info(f"PiP entity found: {pip_file_path}")

        ## hard-coded defaults, which should then be set below
        is_swf_task = False
        
        ## attempt to integrate task_specific render profiles
        render_profile = self._get_render_profile( task_type )
        if render_profile:
            is_swf_task = render_profile["export_swf"]
            #render_source = render_profile["render_source"]
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
        # self.render_source = getattr(self, "self.render_source", None)
        # if not self.render_source:
        #     self.log.warning(f"No render source specified, defaulting to '{self.render_source}'")

        # fixing legacy settings
        if self.render_source == "h264":
            self.render_source = "mp4"

        self.log.info(f"Export SWF: {is_swf_task}" )
        self.log.info(f"Render source mode: {self.render_source}" )


        if self.render_source == "png":
            self.log.info(f"Exporting PNG sequence to {staging_dir}")
            self._export_png_sequence(output_path)

            frame_files = self._collect_exported_frames(staging_dir, output_basename)
            if not frame_files:
                raise RuntimeError(
                    f"No PNG frames exported to {staging_dir}"
                )
            self.log.info(f"Exported {len(frame_files)} frames")
            frame_output = frame_files[self.frame_start:self.frame_end]
            mp4_output = self._convert_sequence_to_mp4(staging_dir,output_basename)
            self.log.info(f"Converted PNG sequence to MP4: {mp4_output}")
        else:
            self.log.info(f"Exporting mov to {staging_dir}")
            movie = self.export_movie(output_path)
            video_output = self._adjust_mov_paths(movie, staging_dir, output_basename)

            if self.render_source == "mp4":
                mp4_output = self._convert_movie_to_mp4(
                    video_output,
                    staging_dir,
                    output_basename,
                )
                self.log.info(f"Converted QuickTime movie to MP4: {mp4_output}")

                # adding picture-in-picture
                if pip_file_path:
                    mp4_output = self._add_pip_to_render(
                        mp4_output,
                        pip_file_path,
                        staging_dir,
                        output_basename
                    )
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
        
        # This is where we define the representations for the extracted media. Can change this to include the mp4 option instead or as well. 
        if self.render_source == "mov":
            representation = {
                "name": "mov",
                "ext": "mov",
                "files": video_output,
                "stagingDir": staging_dir,
                "frameStart": self.frame_start,
                "frameEnd": self.frame_end,
                "fps": self.fps,
                "tags": ["review"],
            }
        else:
            representation = {
                "name": "mp4",
                "ext": "mp4",
                "files": mp4_output,
                "stagingDir": staging_dir,
                "frameStart": self.frame_start,
                "frameEnd": self.frame_end,
                "fps": self.fps,
                "tags": ["review"],
            }
        instance.data["representations"].append(representation)

        if self.render_source == "png":
            png_representation = {
                "name": "png",
                "ext": "png",
                "files": frame_output,
                "stagingDir": staging_dir,
                "frameStart": self.frame_start,
                "frameEnd": self.frame_end,
                "tags": [],
            }
            instance.data["representations"].append(png_representation)

        if swf_output:
            swf_representation = {
                "name": "swf",
                "ext": "swf",
                "files": swf_output,
                "stagingDir": staging_dir,
                "frameStart": self.frame_start,
                "frameEnd": self.frame_end,
                "fps": self.fps,
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

        frame_length = self.frame_end-self.frame_start
        bg_colour = getattr(self,"png_bg_colour","#666666")

        png_pattern = os.path.join(staging_dir, f"{basename}%04d.png")
        args = [
            "-y",
            "-framerate",
            "25",
            "-start_number",
            str(self.start_frame),
            "-i",
            png_pattern,
            "-frames:v",
            str(frame_length),
            "-filter_complex",
            f"color='{bg_colour}',format=rgb24[c];[c][0]scale2ref[c][i];[c][i]overlay=format=auto:shortest=1,setsar=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            mp4_path,
        ]
        self.log.debug(args)
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

    def _get_pip_entity(self, instance):
        if not "target_product" in self.pip_settings:
            self.log.info("No target_product defined in PiP settings.")
            return None
        target_product = self.pip_settings["target_product"]
        # Picture in picture
        project_name = instance.data["projectEntity"]["name"]
        folder_data = instance.data["folderEntity"]
        # check it exists and get latest version
        pip_entity = ayon_api.get_last_version_by_product_name(
            project_name,
            target_product,
            folder_data["id"],
            fields=["name","version"]
        )
        if not pip_entity: # no versions found
            return None
        # get anatomy path for pip entity
        anatomy = Anatomy(
            instance.data["projectEntity"]["name"],
            project_entity=instance.data["projectEntity"]
        )
        anatomy_data = get_template_data(
            instance.data["projectEntity"],
            instance.data["folderEntity"],
            instance.data["taskEntity"]
        )
        anatomy_data["product"] = {
            "type" : "review",
            "name" : target_product,
        }
        anatomy_data["version"] = pip_entity["version"]
        pip_dir_path = anatomy.get_template_item(
            "publish", "shot_render", "directory"
        ).format(anatomy_data)
        # get file
        pip_file_version = "v{0:0>3}".format(pip_entity["version"])
        pip_file_target = "_".join([
            target_product,
            pip_file_version,
            "h264.mp4"
        ])
        pip_file_name = None
        for file in os.listdir(pip_dir_path):
            if pip_file_target in file:
                pip_file_name = file
                break
        if not pip_file_name:
            return None
        ## join filename
        pip_file_path = os.path.join(pip_dir_path, pip_file_name)
        return pip_file_path


    def _get_pip_ffmpeg_args(self):
        # prepare arguments
        settings_template = "[1]scale=iw/{scale_ratio}:ih/{scale_ratio} [pip]; [0][pip] overlay={pos_x}:{pos_y}"
        args = {
            "scale_ratio" : "4",
            "pos_x" : "10",
            "pos_y" : "10",
        }

        # get settings from server
        if not self.pip_settings:
            self.log.info( "No PiP settings found in server. Setting to defaults.")
        else:
            # get scale
            args["scale_ratio"] = str(1 / self.pip_settings.get("pip_scale"))
            # get position from offset
            offset_px = self.pip_settings.get("pip_offset")
            match self.pip_settings.get("pip_position"):
                case "top_left":
                    args["pos_x"] = str(offset_px)
                    args["pos_y"] = str(offset_px)
                case "top_right":
                    args["pos_x"] = f"main_w-overlay_w-{offset_px}"
                    args["pos_y"] = str(offset_px)
                case "bottom_left":
                    args["pos_x"] = str(offset_px)
                    args["pos_y"] = f"main_h-overlay_h-{offset_px}"
                case "bottom_right":
                    args["pos_x"] = f"main_w-overlay_w-{offset_px}"
                    args["pos_y"] = f"main_h-overlay_h-{offset_px}"

        pip_args = settings_template.format(**args)
        self.log.debug(pip_args)
        return pip_args

    def _add_pip_to_render(self, source_mp4, pip_file_path, staging_dir, basename):
        source_path = os.path.join(staging_dir, source_mp4)
        mp4_path = os.path.join(staging_dir, f"{basename}_pip.mp4")

        pip_args = self._get_pip_ffmpeg_args()

        args = [
            "-y",
            "-i",
            source_path,
            "-i",
            pip_file_path,
            "-filter_complex",
            pip_args,
            mp4_path,
        ]

        self._run_ffmpeg(args)
        return os.path.basename(mp4_path)

    def staging_dir(self, instance):
        from ayon_core.pipeline.publish import get_instance_staging_dir
        return get_instance_staging_dir(instance)