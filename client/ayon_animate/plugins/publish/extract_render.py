import subprocess
import os
from pathlib import Path
from ayon_core.lib.vendor_bin_utils import get_ffmpeg_tool_args


import pyblish.api
import ayon_api
from ayon_core.pipeline import (
    publish,
    Anatomy
)
from ayon_core.pipeline.template_data import get_template_data
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
    pip_settings = None
    timeline_length = 0

    def host_trace(self, message):
        return animate.stub().host_trace(message)
 
    def process(self, instance):
        """Extract render instance and output an mp4 representation"""
        self.log.info(f"Extracting render: {instance.data['name']}")

        self.creator_attributes = instance.data.get("creator_attributes")
        self.log.debug(self.creator_attributes)

        # API init
        stub = animate.stub()
        staging_dir = self.staging_dir(instance)
        
        doc_name = stub.get_active_document_name()
        if not doc_name:
            raise RuntimeError("No active Animate document")
        self.timeline_length = stub.get_timeline_length()

        file_basename = Path(doc_name).stem
        instance_name = instance.data["name"]
        task_type = instance.data.get("task")
        output_basename = f"{file_basename}_{instance_name}"
        output_path = os.path.join(staging_dir, output_basename)


        # render settings from 
        render_source = self._get_render_source(instance.data)
        frame_start = instance.data.get("frameStart", 1)
        frame_end = instance.data.get("frameEnd", self.timeline_length)
        fps =  instance.data.get("fps", 25)
        self.log.info( f"Start frame: {frame_start}; End frame: {frame_end}; FPS: {fps}")

        # png renderer handling
        if render_source == "png":
            # fetch and validate render type
            frame_range_string = self.creator_attributes.get("frame_range",False)
            if not frame_range_string or frame_range_string == f"1-{self.timeline_length}":
                frame_range = "all"
            else:
                frame_range = self._get_png_frame_range(frame_range_string)
                self.log.debug(f"PNG exporter will export frames: {str(frame_range)}")
            ## whether or not to include PNGs
            if not "include_pngs" in self.creator_attributes:
                self.creator_attributes["include_pngs"] = False
        
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
            
        self.log.info(f"Export SWF: {is_swf_task}" )
        self.log.info(f"Render source mode: {render_source}" )


        if render_source == "png":
            self.log.info(f"Exporting PNG sequence to {staging_dir}")
            if frame_range == "all":
                self._export_png_sequence(output_path)
            else:
                self._export_png_range(output_path,frame_range)

            frame_files = self._collect_exported_frames(staging_dir, output_basename)
            if not frame_files:
                raise RuntimeError(
                    f"No PNG frames exported to {staging_dir}"
                )
            self.log.info(f"Exported {len(frame_files)} frames")

            # first_frame = max(0,frame_start-1)
            # frame_output = frame_files[first_frame:frame_end]
            mp4_output = self._convert_sequence_to_mp4(staging_dir,output_basename)
            self.log.info(f"Converted PNG sequence to MP4: {mp4_output}")
        else:
            self.log.info(f"Exporting mov to {staging_dir}")
            movie = self.export_movie(output_path)
            video_output = self._adjust_mov_paths(movie, staging_dir, output_basename)

            if render_source == "mp4":
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
        if render_source == "mov":
            representation = {
                "name": "mov",
                "ext": "mov",
                "files": video_output,
                "stagingDir": staging_dir,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "fps": fps,
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
                "fps": fps,
                "tags": ["review"],
            }
        instance.data["representations"].append(representation)

        if render_source == "png" and self.creator_attributes["include_pngs"]:
            if len(frame_files) > 1:
                png_representation = {
                    "name": "png",
                    "ext": "png",
                    "files": frame_files,
                    "stagingDir": staging_dir,
                    "frameStart": frame_start,
                    "frameEnd": frame_end,
                    "tags": [],
                }
                instance.data["representations"].append(png_representation)
            else:
                png_representation = {
                    "name": "png",
                    "ext": "png",
                    "files": frame_files[0],
                    "stagingDir": staging_dir,
                    "tags": [],
                }
                instance.data["representations"].append(png_representation)         

        if swf_output:
            swf_representation = {
                "name": "swf",
                "ext": "swf",
                "files": swf_output,
                "stagingDir": staging_dir,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "fps": fps,
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

    def _export_png_range(self,output_path,frame_range):
        export_path = str(output_path).replace("\\", "/")

        for f in range(0,len(frame_range)):
            png_path = export_path + f"{f:04d}"
            result = animate.stub().export_png_frame(png_path,frame_range[f])
            if not result or result is False:
                raise RuntimeError("Failed to export PNG frame from Animate")

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

        # frame_length = (frame_end-frame_start)+1
        bg_colour = getattr(self,"png_bg_colour","#666666")

        png_pattern = os.path.join(staging_dir, f"{basename}%04d.png")
        args = [
            "-y",
            "-framerate",
            "25",
            # "-start_number",
            # str(frame_start),
            "-i",
            png_pattern,
            # "-frames:v",
            # str(frame_length),
            "-filter_complex",
            f"color='{bg_colour}',format=rgb24[c];[c][0]scale2ref[c][i];[c][i]overlay=format=auto:shortest=1,setsar=1",
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

    def _get_pip_entity(self, instance):
        folder_entity = instance.data["folderEntity"]
        folder_type = folder_entity["folderType"].lower()
        match folder_type:
            case "shot":
                target_product = "reviewReference"
                target_product_type = "review"
            case "sequence":
                target_product = "renderBuild_animatic_refMain"
                target_product_type = "render"
        
        # target_product = self.pip_settings["target_product"]
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
            "type" : target_product_type,
            "name" : target_product,
        }
        anatomy_data["version"] = pip_entity["version"]
        pip_dir_path = anatomy.get_template_item(
            "publish", f"{folder_type}_render", "directory"
        ).format(anatomy_data)
        # get file
        pip_file_version = "v{0:0>3}".format(pip_entity["version"])
        pip_file_target = "_".join([
            target_product,
            pip_file_version,
            "h264.mp4"
        ])
        pip_file_name = None
        if not os.path.exists(pip_dir_path):
            self.log.info(f"could not find any files in {pip_dir_path}")
            return None
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
            self.log.debug(self.pip_settings)
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
                case "btm_left":
                    args["pos_x"] = str(offset_px)
                    args["pos_y"] = f"main_h-overlay_h-{offset_px}"
                case "btm_right":
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

    def _get_render_source(self, data):
        render_source = data.get("renderSource",None)
        if not render_source:
            return "mp4"
        if render_source in ["png","mp4","mov"]:
            return render_source
        else:
            return "mp4"

    def _get_png_frame_range(self,frame_string):
        # sanitise
        clean_frame_string = frame_string
        valid_chars = ["0","1","2","3","4","5","6","7","8","9","-",","]
        unique_chars = list(dict.fromkeys([c for c in frame_string]))
        for char in unique_chars:
            if char not in valid_chars:
                clean_frame_string = clean_frame_string.replace(char,"")
        # validate list
        frame_list = clean_frame_string.split(",")
        if len(frame_list) == 0:
            if frame_string.isdigit():
                return [int(frame_string)]
            else:
                raise RuntimeError(f"""Could not parse frame_range '{frame_string}' to a valid frame range.
Check the formatting is correct. Frame ranges should only contain numeric characters,
commas and dashes (i.e. '1-5,6,10')""")
        # now we convert
        frames = []
        for frame_range in frame_list:
            if "-" in frame_range: # single frame
                frames += self._range_to_int(frame_range)
            elif frame_range.isdigit():
                frames.append(int(frame_range))
            else:
                raise RuntimeError(f"Frame range of '{frame_string}' is invalid at value: '{frame_range}'")
        self.log.debug(f"frame range pre-validation: {frames}")
        frames = self._validate_frame_range(frames)
        if len(frames) == 0:
                raise RuntimeError(f"""Could not parse frame_range '{frame_string}' to a valid frame range.
Check the formatting is correct. Frame ranges should only contain numeric characters,
commas and dashes (i.e. '1-5,6,10')""")
        return frames

    def _range_to_int(self,range_string):
        frames = []
        frame_range = range_string.split("-")
        match len(frame_range):
            case 1:
                frames.append(int(frame_range[0]))
            case 2:
                # validate
                try:
                    start_frame = abs(int(frame_range[0]))
                    end_frame = abs(int(frame_range[1]))
                except Exception as e:
                    raise RuntimeError(f"Could not get start and end frames for '{frame_range}': {e}.")
                if start_frame == end_frame:
                    frames.append(start_frame)  
                elif start_frame < end_frame:
                    for f in range(start_frame,end_frame+1):
                        frames.append(f)
                else:
                    raise RuntimeError(f"Could not parse '{frame_range}'. Second value is lower than first value.")
            case _:
                raise RuntimeError(f"Could not parse '{frame_range}'. More than two values detected.")
        return frames

    def _validate_frame_range(self,frame_range):
        frames_out=[]
        for frame in frame_range:
            # remove frames outside frame range
            if (frame <= 0) or (frame > self.timeline_length):
                self.log.debug(f"skipping frame {frame} as this is outside the timeline range (expecting 1 to {self.timeline_length})")
                continue
            # skip duplicates
            if frame in frames_out:
                continue
            frames_out.append(frame)
        frames_out.sort()
        return frames_out