import ipywidgets as ipyw
import matplotlib.pyplot as plt
import numpy as np

class ImageSliceCompare3D:
    """ 
    ImageSliceViewer3D is for viewing volumetric image slices in jupyter or
    ipython notebooks. 
    
    User can interactively change the slice plane selection for the image and 
    the slice plane being viewed. 

    Argumentss:
    Volume = 3D input image
    figsize = default(8,8), to set the size of the figure
    cmap = default('plasma'), string for the matplotlib colormap. You can find 
    more matplotlib colormaps on the following link:
    https://matplotlib.org/users/colormaps.html
    
    """
    
    def __init__(self, volume,volume2,mini,maxi,figsize=(8,8), cmap='gray',):
        self.volume = volume
        self.volume2 = volume2  
        self.figsize = figsize
        self.cmap = cmap
        self.v = [mini, maxi]
        
        # Call to select slice plane
        ipyw.interact(self.view_selection, view=ipyw.RadioButtons(
            options=['x-y','y-z', 'z-x'], value='x-y', 
            description='Slice plane selection:', disabled=False,
            style={'description_width': 'initial'}))
    
    def view_selection(self, view):
        # Transpose the volume to orient according to the slice plane selection
        orient = {"y-z":[1,2,0], "z-x":[2,0,1], "x-y": [0,1,2]}
        self.vol = np.transpose(self.volume, orient[view])
        self.vol2 = np.transpose(self.volume2, orient[view])
        maxZ = self.vol.shape[2] - 1
        
        # Call to view a slice within the selected slice plane
        ipyw.interact(self.plot_slice, 
            z=ipyw.IntSlider(min=0, max=maxZ, step=1, continuous_update=True, 
            description='Image Slice:'))
        
    def plot_slice(self, z):
        # Plot slice for the given plane and slice
        self.fig = plt.figure(figsize=self.figsize)
        plt.imshow(self.vol[:,:,z], cmap=plt.get_cmap(self.cmap), 
            vmin=self.v[0], vmax=self.v[1])
        
        self.fig2 = plt.figure(figsize=self.figsize)
        plt.imshow(self.vol2[:,:,z], cmap=plt.get_cmap(self.cmap), 
            vmin=self.v[0], vmax=self.v[1])
        
        
class ImageSliceViewer3D:
    """ 
    ImageSliceViewer3D is for viewing volumetric image slices in jupyter or
    ipython notebooks. 
    
    User can interactively change the slice plane selection for the image and 
    the slice plane being viewed. 

    Argumentss:
    Volume = 3D input image
    figsize = default(8,8), to set the size of the figure
    cmap = default('plasma'), string for the matplotlib colormap. You can find 
    more matplotlib colormaps on the following link:
    https://matplotlib.org/users/colormaps.html
    
    """
    
    def __init__(self, volume,mini,maxi,figsize=(8,8), cmap='gray',step_size=1.0):
        self.volume = volume
        self.figsize = figsize
        self.cmap = cmap
        self.v = [mini, maxi]
        #guarantee minimum number of steps
        tst=(maxi-mini)/20
        self.step_size=np.min([step_size,tst])
        
        # Call to select slice plane
        ipyw.interact(self.view_selection, view=ipyw.RadioButtons(
            options=['x-y','y-z', 'z-x'], value='x-y', 
            description='Slice plane selection:', disabled=False,
            style={'description_width': 'initial'}))
    
    def view_selection(self, view):
        # Transpose the volume to orient according to the slice plane selection
        orient = {"y-z":[1,2,0], "z-x":[2,0,1], "x-y": [0,1,2]}
        self.vol = np.transpose(self.volume, orient[view])
        maxZ = self.vol.shape[2] - 1
        
        # Call to view a slice within the selected slice plane
        ipyw.interact(self.plot_slice, 
            z=ipyw.IntSlider(min=0, max=maxZ, step=1, continuous_update=True, 
            description='Image Slice:'),
            m=ipyw.FloatRangeSlider(min=self.v[0],max=self.v[1],
                    readout_format='1.3f',value=[self.v[0],self.v[1]],
                    step=self.step_size, description='Disp Rng:',
                    layout={'width':'350px'}))
        
    def plot_slice(self, z, m):
        # Plot slice for the given plane and slice
        self.fig = plt.figure(figsize=self.figsize)
        plt.imshow(self.vol[:,:,z], cmap=plt.get_cmap(self.cmap), 
            vmin=m[0], vmax=m[1])
            
            
class ImageSliceViewer4D:
    """
    ImageSliceViewer4D is for viewing volumetric image slices and bins/timepoints in jupyter or
    ipython notebooks.
    
    User can interactively change the slice and bin/timepoint plane selection for the image and
    the slice plane being viewed.

    Argumentss:
    Volume = 4D input image
    figsize = default(8,8), to set the size of the figure
    cmap = default('plasma'), string for the matplotlib colormap. You can find
    more matplotlib colormaps on the following link:
    https://matplotlib.org/users/colormaps.html
    
    """
    
    def __init__(self, volume,mini,maxi,figsize=(8,8), cmap='gray',):
        self.volume = volume
        self.figsize = figsize
        self.cmap = cmap
        self.v = [mini, maxi]
        # Call to select slice plane
        ipyw.interact(self.view_selection, view=ipyw.RadioButtons(
            options=['x-y','y-z', 'z-x'], value='x-y',
            description='Slice plane selection:', disabled=False,
            style={'description_width': 'initial'}))
    
    def view_selection(self, view):
        # Transpose the volume to orient according to the slice plane selection
        orient = {"y-z":[1,2,0,3], "z-x":[2,0,1,3], "x-y": [0,1,2,3]}
        self.vol = np.transpose(self.volume, orient[view])
        maxZ = self.vol.shape[2] - 1
        maxT = self.vol.shape[3] - 1
        
        # Call to view a slice within the selected slice plane
        ipyw.interact(self.plot_slice,
            z=ipyw.IntSlider(min=0, max=maxZ, step=1, continuous_update=True,
            description='Image Slice:'),
            t=ipyw.IntSlider(min=0, max=maxT,step=1, continuous_upate=True,
                               description='Timepoint/Bin:'))
        
    def plot_slice(self, z, t):
        # Plot slice for the given plane and slice
        self.fig = plt.figure(figsize=self.figsize)
        plt.imshow(self.vol[:,:,z,t], cmap=plt.get_cmap(self.cmap),
            vmin=self.v[0], vmax=self.v[1]) #self.v[1])
            
            
class ImageTraceViewerSingle:
    
    def __init__(self, volume,mini,maxi,figsize=(8,8), cmap='gray',):
        self.volume = volume
        self.figsize = figsize
        self.cmap = cmap
        self.v = [mini, maxi]
     
    
        # Call to select slice plane
        ipyw.interact(self.view_selection, view=ipyw.RadioButtons(
            options=['x-y','y-z', 'z-x'], value='x-y', 
            description='Slice plane selection:', disabled=False,
            style={'description_width': 'initial'}))
        

    def view_selection(self, view):
        # Transpose the volume to orient according to the slice plane selection
        orient = {"y-z":[1,2,0], "z-x":[2,0,1], "x-y": [0,1,2]}
        self.vol = np.transpose(self.volume, orient[view])
        maxX = self.vol.shape[0] - 1
        maxY = self.vol.shape[1] - 1
        maxZ = self.vol.shape[2] - 1
        
        
        ipyw.interact(self.plot_slice, 
            y=ipyw.IntSlider(value=0,min=0, max=maxY, step=1, continuous_update=True, 
            description='X Position:'), 
            x=ipyw.IntSlider(value=0,min=0, max=maxX, step=1, continuous_update=True, 
            description='Y Position:'), 
            z=ipyw.IntSlider(value=0,min=0, max=maxZ, step=1, continuous_update=True, 
            description='Image Slice:'))
        
        
    def plot_slice(self,x,y,z):
        # Plot slice for the given plane and slice
        self.fig = plt.figure(figsize=self.figsize)
        plt.imshow(self.vol[:,:,z], cmap=plt.get_cmap(self.cmap), 
            vmin=self.v[0], vmax=self.v[1])
        
        maxX = self.vol.shape[0] - 1
        maxY = self.vol.shape[1] - 1
        maxZ = self.vol.shape[2] - 1

        yvec = np.arange(0,maxY)
        xvec = np.ones(yvec.shape)*x
        plt.plot(yvec,xvec,'bo')

        xvec = np.arange(0,maxX)
        yvec = np.ones(xvec.shape)*y
        plt.plot(yvec,xvec,'ro')

        self.fig2 = plt.figure(figsize=self.figsize)
        plt.plot(self.vol[x,:,z],'b')
        plt.title("X Profile")

        
        self.fig3 = plt.figure(figsize=self.figsize)
        plt.plot(self.vol[:,y,z],'r')
        plt.title("Y Profile")

        
class ImageTraceViewerDouble:
    
    def __init__(self, volume,volume2,mini,maxi,figsize=(10,10), cmap='gray',):
        self.volume = volume
        self.volume2 = volume2  
        self.figsize = figsize
        self.cmap = cmap
        self.v = [mini, maxi]
        
        # Call to select slice plane
        ipyw.interact(self.view_selection, view=ipyw.RadioButtons(
            options=['x-y','y-z', 'z-x'], value='x-y', 
            description='Slice plane selection:', disabled=False,
            style={'description_width': 'initial'}))
    
    def view_selection(self, view):
        # Transpose the volume to orient according to the slice plane selection
        orient = {"y-z":[1,2,0], "z-x":[2,0,1], "x-y": [0,1,2]}
        self.vol = np.transpose(self.volume, orient[view])
        self.vol2 = np.transpose(self.volume2, orient[view])
        
        
        maxX = self.vol.shape[0] - 1
        maxY = self.vol.shape[1] - 1
        maxZ = self.vol.shape[2] - 1
        
        
        ipyw.interact(self.plot_slice, 
            y=ipyw.IntSlider(value=0,min=0, max=maxY, step=1, continuous_update=True, 
            description='X Position:'), 
            x=ipyw.IntSlider(value=0,min=0, max=maxX, step=1, continuous_update=True, 
            description='Y Position:'), 
            z=ipyw.IntSlider(value=0,min=0, max=maxZ, step=1, continuous_update=True, 
            description='Image Slice:'))
            
    def plot_slice(self, x,y,z):
        # Plot slice for the given plane and slice
        self.fig, self.ax = plt.subplots(2,2)          
        self.fig.set_figheight(self.figsize[0])
        self.fig.set_figwidth(self.figsize[1])
        
        #self.fig = plt.figure(figsize=self.figsize)

        maxX = self.vol.shape[0] - 1
        maxY = self.vol.shape[1] - 1
        maxZ = self.vol.shape[2] - 1
        
        
        yvec1 = np.arange(0,maxY)
        xvec1 = np.ones(yvec1.shape)*x

        xvec2 = np.arange(0,maxX)
        yvec2 = np.ones(xvec2.shape)*y
        
        self.ax[0,0].imshow(self.vol[:,:,z], cmap=plt.get_cmap(self.cmap), 
            vmin=self.v[0], vmax=self.v[1])

        self.ax[0,0].plot(yvec1,xvec1,'bo')
        self.ax[0,0].plot(yvec2,xvec2,'ro')

        self.ax[0,1].imshow(self.vol2[:,:,z], cmap=plt.get_cmap(self.cmap), 
            vmin=self.v[0], vmax=self.v[1])

        self.ax[0,1].plot(yvec1,xvec1,'go')
        self.ax[0,1].plot(yvec2,xvec2,'yo')
        
        self.ax[1,0].plot(self.vol[x,:,z],'b')
        self.ax[1,0].plot(self.vol2[x,:,z],'g')
        self.ax[1,0].set(title="X Profile")

        self.ax[1,1].plot(self.vol[:,y,z],'r')
        self.ax[1,1].plot(self.vol2[:,y,z],'y')
        self.ax[1,1].set(title="Y Profile")
        
class SpectralBinViewer:
    
    def __init__(self, volume,mini,maxi,figsize=(8,8), cmap='gray',):
        self.volume = volume
        self.figsize = figsize
        self.cmap = cmap
        self.v = [mini, maxi]
     
    
        # Call to select slice plane
        ipyw.interact(self.view_selection, view=ipyw.RadioButtons(
            options=['x-y','y-z', 'z-x'], value='x-y', 
            description='Slice plane selection:', disabled=False,
            style={'description_width': 'initial'}))
        

    def view_selection(self, view):
        # Transpose the volume to orient according to the slice plane selection
        orient = {"y-z":[1,2,0,3], "z-x":[2,0,1,3], "x-y": [0,1,2,3]}
        self.vol = np.transpose(self.volume, orient[view])
        maxX = self.vol.shape[0] - 1
        maxY = self.vol.shape[1] - 1
        maxZ = self.vol.shape[2] - 1
        maxB = self.vol.shape[3] - 1
      
        
        
        ipyw.interact(self.plot_slice, 
            y=ipyw.IntSlider(value=0,min=0, max=maxY, step=1, continuous_update=True, 
            description='X Position:'), 
            x=ipyw.IntSlider(value=0,min=0, max=maxX, step=1, continuous_update=True, 
            description='Y Position:'), 
            z=ipyw.IntSlider(value=0,min=0, max=maxZ, step=1, continuous_update=True, 
            description='View Slice:'),
            b=ipyw.IntSlider(value=0,min=0, max=maxB, step=1, continuous_update=True, 
            description='View Bin:'))
        
        
    def plot_slice(self,x,y,z,b):
        # Plot slice for the given plane and slice
        self.fig = plt.figure(figsize=self.figsize)
        plt.imshow(self.vol[:,:,z,b], cmap=plt.get_cmap(self.cmap), 
            vmin=self.v[0], vmax=self.v[1])
        
        maxX = self.vol.shape[0] - 1
        maxY = self.vol.shape[1] - 1

        yvec = np.arange(0,maxY)
        xvec = np.ones(yvec.shape)*x
        plt.plot(yvec,xvec,'bo')

        xvec = np.arange(0,maxX)
        yvec = np.ones(xvec.shape)*y
        plt.plot(yvec,xvec,'ro')

        self.fig2 = plt.figure(figsize=self.figsize)
        plt.plot(self.vol[x,y,z,:],'bo')
        plt.title("Bin Profile")
