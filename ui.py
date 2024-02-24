from tkinter import *
from PIL import ImageTk, Image
import glob, math, os
from shotBoundary import shortBoundary

ANTIALIAS = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS #just to avoid the warning

#this contains only functions for the UI and necessary calls to the shotBoundary file where mostly its related to the algorithm
class ui(Frame):
    def __init__(self, master):
        self.shortBoundary = shortBoundary()
        self.frame_width = 500
        self.frame_height = 200
        self.selected_index=0
        self.frame_imgs = []
        self.pil_frame_imgs = []
        self.frame_desc = []
        self.frame_ranges = []
        self.check_ui_images() #function call to check if the frames folder has iamges to display for the UI, note this is only used for the Ui and not the algorithm
        self.shortBoundary.check_intensity_values() #check if intensity values file is present else it will generate one, this is done to reduce initial load time
        self.shortBoundary.generate_sd() #generates SD values for the frames
        self.shortBoundary.set_thresholds() #sets threshold for all frames in the range
        self.shortBoundary.find_frames() #finds cuts and Gradual transitions
        self.populate_img_grid() #populates necessary values needed for grid
        Frame.__init__(self, master)
        self.master = master
        self.mainFrame = Frame(master)
        self.mainFrame.columnconfigure(0, weight=1)
        self.mainFrame.columnconfigure(1, weight=5)
        self.mainFrame.rowconfigure(0, weight=1)
        self.mainFrame.pack(fill='both', expand=True)
        self.containerFrame = Frame(self.mainFrame)
        self.containerFrame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.containerFrame.columnconfigure(0, weight=1)
        self.containerFrame.columnconfigure(1, weight=5)
        self.gridFrame = Frame(self.containerFrame)
        self.gridFrame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.gridFrame.columnconfigure(0, weight=1) 
        self.convert_pil_imgs() #converts all frames to PIL iamges to display in the UI
        self.create_image_grid() #creates the 3*10 grid and adds images into it
        img = Image.open(f".\\display.jpg") #adds a placeholder 
        img = img.resize((self.frame_width, self.frame_height), ANTIALIAS)
        self.chosen_frame = ImageTk.PhotoImage(img)
        self.frameLabel = Label(self.containerFrame, width=500, height=300, bg="black", image=self.chosen_frame)
        self.frameLabel.grid(column=0, row=0, sticky=NS, padx=1, pady=5)  
        self.resultsFrame = Frame(self.containerFrame)
        self.resultsFrame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew") 
        #creates label for reuslts to be displayed in UI
        self.csceLabel = Label(self.resultsFrame, text="Cuts (Cs, Ce): ", font=("Arial", 12))
        self.csceLabel.grid(row=0, column=0, sticky="w")
        self.fefsLabel = Label(self.resultsFrame, text="Gradual Transitions (Fs, Fe): ", font=("Arial", 12))
        self.fefsLabel.grid(row=0, column=1, sticky="w")
        cs_pairs = [(self.shortBoundary.frame_results["cs"][i], self.shortBoundary.frame_results["ce"][i]) for i in range(len(self.shortBoundary.frame_results["cs"]))]
        fe_pairs = [(self.shortBoundary.frame_results["fs"][i], self.shortBoundary.frame_results["fe"][i]) for i in range(len(self.shortBoundary.frame_results["fs"]))]
        cs_text = "\n".join([f"{cs[0]:<5}, {cs[1]:<5}" for cs in cs_pairs])
        fe_text = "\n".join([f"{fe[0]:<5}, {fe[1]:<5}" for fe in fe_pairs])
        self.csceLabel.config(text=f"Cuts (Cs, Ce):\n{cs_text}")
        self.fefsLabel.config(text=f"Gradual Transitions (Fs, Fe):\n{fe_text}")
        self.csceLabel.grid(row=0, column=0, sticky="nw")
 
    #plays video from a given frame as selected in the UI
    def play_from_frame(self, frame=0):
        selected_frame_index = self.selected_index
        frame_set = self.frame_ranges[selected_frame_index]  
        i = frame_set[0] + frame
        if i - self.shortBoundary.start_frame > frame_set[1] - self.shortBoundary.start_frame: 
            return
        pil_frame = self.pil_frame_imgs[i - self.shortBoundary.start_frame]
        self.frameLabel.configure(image=pil_frame)
        self.frameLabel.image = pil_frame
        root.after(15, self.play_from_frame, frame+1)

    #creates the 3*10 grid and adds images into it, this function is only related to the UI
    def create_image_grid(self):
        self.gridFrame = Frame(self.mainFrame)
        self.gridFrame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        for i in range(10):
            self.gridFrame.rowconfigure(i * 3, weight=1)
            self.gridFrame.rowconfigure(i * 3 + 1, weight=0)
            self.gridFrame.rowconfigure(i * 3 + 2, weight=0)
            self.gridFrame.columnconfigure(i, weight=1)
        image_width = 100
        image_height = 80
        for i, shot in enumerate(self.frame_ranges):
            path=rf".\\frames\frame{shot[0]}.jpg"
            img = Image.open(path)
            img = img.resize((image_width, image_height), ANTIALIAS)
            photo = ImageTk.PhotoImage(img)
            row = (i // 10) * 3
            col = i % 10
            image_label = Label(self.gridFrame, image=photo)
            image_label.image = photo  
            image_label.grid(row=row, column=col, padx=5, pady=5)
            image_label.bind("<Button-1>", lambda event, index=i: self.play_video_from(index))  
            shot_number_label = Label(self.gridFrame, text=f"S{i + 1}", font=("Arial", 8))
            shot_number_label.grid(row=row + 1, column=col, sticky="n")
            frame_number_label = Label(self.gridFrame, text=f"Frame {shot[0]}", font=("Arial", 8))
            frame_number_label.grid(row=row + 2, column=col, sticky="n")

    #initial call when a image is clicked in the GRID in UI
    def play_video_from(self, index):
        self.selected_index=index
        frame=0
        selected_frame_index = index
        frame_set = self.frame_ranges[selected_frame_index]  
        frame_set = self.frame_ranges[selected_frame_index] 
        i = frame_set[0] + frame
        if i - self.shortBoundary.start_frame > frame_set[1] - self.shortBoundary.start_frame:  
            return
        pil_frame = self.pil_frame_imgs.__getitem__(index)
        self.frameLabel.configure(image=pil_frame)
        self.frameLabel.image = pil_frame
        root.after(15, self.play_from_frame, frame+1)
       
    #converts all frames to PIL iamges to display in the UI
    def convert_pil_imgs(self):
        path = r".\frames\*.jpg"
        for infile in (glob.glob(path)):
            im = Image.open(infile)
            imResize = im.resize((self.frame_width, self.frame_height), ANTIALIAS)
            photo = ImageTk.PhotoImage(imResize)
            self.pil_frame_imgs.append(photo)
    #populates necessary values needed for grid , this is only for the UI
    def populate_img_grid(self):
        start_frames = [self.shortBoundary.start_frame]
        for ce_frame in self.shortBoundary.frame_results["ce"]:
            start_frames.append(ce_frame)
       
        for fs_frame in self.shortBoundary.frame_results["fs"]:
            start_frames.append(fs_frame + 1)
        
        start_frames.sort()
        end_frames = [self.shortBoundary.end_frame]
        for cs_frame in self.shortBoundary.frame_results["cs"]:
            end_frames.append(cs_frame)
        for fs_frame in self.shortBoundary.frame_results["fs"]:
            end_frames.append(fs_frame)
        end_frames.sort()
        for i in range(len(start_frames)):
            if i==0:
                continue
            shot = (start_frames[i], end_frames[i])
            self.frame_ranges.append(shot)
            self.frame_desc.append(str(start_frames[i]))            
        for shot in self.frame_ranges:
            path=rf".\\frames\frame{shot[0]}.jpg"
            im = Image.open(path)
            imResize = im.resize((self.frame_width, self.frame_height), ANTIALIAS)
            photo = ImageTk.PhotoImage(imResize)
            self.frame_imgs.append(photo)
        
    #function to check if the frames folder has iamges to display for the UI, note this is only used for the Ui and not the algorithm,
    #this is done to reduce the initial load time
    def check_ui_images(self):
        path = r".\\frames"
        dir = os.listdir(path)
        if len(dir) == 0:  #if there are no images for UI, it will generate images for UI 
            self.shortBoundary.extract_frames_for_ui()
            return False
        else:
            return True

if __name__ == '__main__':
    root = Tk()
    root.state('zoomed')
    root.title('Shot Boundary Detection')
    imageViewer = ui(root)
    root.mainloop()