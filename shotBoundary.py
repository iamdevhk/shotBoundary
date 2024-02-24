import cv2
import os
import numpy as np

class shortBoundary:
    def __init__(self):
        self.video_path= r".\\20020924_juve_dk_02a_1.avi"
        self.frame_resolution = 0
        self.frame_width = 500
        self.frame_height = 200
        self.start_frame = 1000
        self.end_frame = 4999
        self.pil_imgs = []
        self.intensity_bins = np.array([])
        self.sd_values = []
        self.tb = 0
        self.ts = 0
        self.tor = 2
        self.frame_results = {"cs" : [], "ce" : [], "fs" : [], "fe" : []}
        self.frame_images = []

    #check if intensity values file is present else it will generate one, this is done to reduce initial load time    
    def check_intensity_values(self):
        file_name = r".\\intensity_bins"
        if os.path.exists(file_name):
            self.intensity_bins = self.load_intensity_values()
            self.intensity_bins = np.array(self.intensity_bins).tolist()
        
        else:
            self.create_intensity_values()
    #loads intensity values from the stored file which is generated when its not present
    def load_intensity_values(self):
        return self.read_intensity_file("intensity_bins")
    
    #gets the frames dimensions
    def get_frame_dimensions(self):
        vidcap = cv2.VideoCapture(self.video_path)
        success, image = vidcap.read()
        self.frame_width = image.shape[1]
        self.frame_height = image.shape[0] 
        self.frame_resolution = self.frame_width * self.frame_height
    #this function  extracts frames for UI, this is only used for the UI and not the algorithm
    def extract_frames_for_ui(self):
        vidcap = cv2.VideoCapture(self.video_path)
        success, image = vidcap.read()
        self.frame_width = image.shape[1]
        self.frame_height = image.shape[0] 
        self.frame_resolution = self.frame_width * self.frame_height
        count = 0
        path= r".\\frames"
        while success:
            while count < self.start_frame:
                success,image = vidcap.read()
                count += 1
            if (count <= self.end_frame):
                filepath = os.path.join(path, "frame%d.jpg" % count)
                cv2.imwrite(filepath, image)  
                
                img = cv2.imread(filepath)
                self.pil_imgs.append(img)
                
                success,image = vidcap.read()
                count += 1
                continue
            break
    #helper function to find the intenisty values given an rgb_img
    def find_intensity_values(self,rgb_image):
        intensity = np.dot(rgb_image[..., :3], [0.299, 0.587, 0.114])
        return np.histogram(intensity, bins=np.arange(0, 256, 10))[0]
    
    #This is the main function for intenisty values where we open the Video iterate through frames till end limit, and if the frames are in given range of 1000 to 4999
    #we find its intensity values and add it to a list
    def create_intensity_values(self):
        
        vidcap = cv2.VideoCapture(self.video_path)
        if not vidcap.isOpened():
            print("Error: The video file could not be opened")
            return None  
        frames_to_process = range(1000, 5000)
        intensity_histograms = []
        for frame_index in range(0,5000): #iterate till 5000
            ret, frame = vidcap.read()
            if not ret:
                break
            if frame_index in frames_to_process: #if in range of 1000 - 5000
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                intensity_histogram = self.find_intensity_values(rgb_frame) #calculate intensity bins
                intensity_histograms.append(intensity_histogram)
        vidcap.release()
        self.intensity_bins = np.array(intensity_histograms)
        self.save_to_file(self.intensity_bins, "intensity_bins") 
        return self.intensity_bins

    #to save the inetnsity values, note this is called only when the file is missing, its done to reduce the initial load time
    def save_to_file(self, data, file_name):
        try:
            file = open(file_name, "wb") 
            np.save(file, data) 
        except Exception:
            print("There's an issue in saving: " + str(Exception))
        finally:
            file.close
    
    #reads intensity values from a file,its done to reduce the initial load time
    def read_intensity_file(self, file_name):
        data = None
        try:
            file = open(file_name, "rb")
            data = np.load(file) 
        except Exception:
            print("There's an issue in reading : " + str(Exception)) 
        finally:
            file.close
            return data
        
    #generates SD values for the frames   
    def generate_sd(self):
        for i in range(0, len(self.intensity_bins) - 1):
            first_histogram = self.intensity_bins[i]
            second_histogram = self.intensity_bins[i + 1]
            sub = np.subtract(first_histogram, second_histogram)
            self.sd_values.append(np.sum(np.abs(sub)))

    #sets threshold values ts and tb
    def set_thresholds(self):
        self.sd_values = np.array(self.sd_values)
        self.ts = np.mean(self.sd_values) * 2
        self.tb = np.mean(self.sd_values) + np.std(self.sd_values) * 11
        
    #finds cuts and Gradual transitions using the algoithm specified    
    def find_frames(self):
        fs_candi = 0  
        fe_candi = 0 
        next_frame_index = 0
        tor = 0   #initializing it to 0 for logic purposes
        cs = 0  
        ce = 0
         # Loop through the SD values of frames
        for frame_index in range(len(self.sd_values)):
            if frame_index <= next_frame_index:
                continue # Skip frames until reaching the next frame to be processed

            if self.sd_values[frame_index] >= self.tb: #if greater than tb its a CUT
                cs = frame_index
                ce = frame_index + 1
                # Store the start and end indexs of the cut in the frame results
                self.frame_results["cs"].append(cs + self.start_frame)
                self.frame_results["ce"].append(ce + self.start_frame)
                next_frame_index = ce
            elif self.ts <= self.sd_values[frame_index] < self.tb: #if its in ts and tb range 
                fs_candi = frame_index
                for trans_frame_index in range(frame_index + 1, len(self.sd_values)):
                    if self.ts <= self.sd_values[trans_frame_index] < self.tb:
                        tor = 0
                        continue
                    elif self.sd_values[trans_frame_index] < self.ts:
                        tor += 1
                        if tor == 2:  
                            fe_candi = trans_frame_index - 2
                            self.find_frames_util(fs_candi, fe_candi) # call helper function to process the gradual transition
                            next_frame_index = fe_candi  # Update next frame index to skip to
                            tor = 0 
                            break
                        continue
                    elif self.sd_values[trans_frame_index] >= self.tb:
                        tor = 0
                        fe_candi = trans_frame_index - 1
                        self.find_frames_util(fs_candi, fe_candi) # call helper function to process the gradual transition
                        next_frame_index = fe_candi  # Update next frame index to skip to
                        break

    #checks if the sum of SD's in a given range is > tb, it qualifies as gradual transition only if it satisfies this
    def find_frames_util(self, fs_candi, fe_candi):
        sd_total = 0
        for sd_ind in range(fs_candi, fe_candi + 1):
            sd_total += self.sd_values[sd_ind]    #sum SD's
        if sd_total >= self.tb: #if > tb its a Gradual transition
            fs = fs_candi
            fe = fe_candi
            self.frame_results["fs"].append(fs + self.start_frame)
            self.frame_results["fe"].append(fe + self.start_frame)
        