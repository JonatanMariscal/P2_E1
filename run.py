import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
import SimpleITK as sitk


def resample_image(image, reference):
    pixel_spacing = image.GetSpacing()
    new_spacing = [old_sz * old_spc / new_sz for old_sz, old_spc, new_sz in
                   zip(image.GetSize(), pixel_spacing, reference.GetSize())]

    image_resampled = sitk.Resample(image, reference.GetSize(), sitk.Transform(), sitk.sitkNearestNeighbor,
                                    image.GetOrigin(), new_spacing,
                                    image.GetDirection(), 0.0, image.GetPixelIDValue())
    return image_resampled


# Register two images with same shape.
def register_images(image, reference):
    initial_transform = sitk.CenteredTransformInitializer(sitk.Cast(reference, image.GetPixelID()),
                                                          image,
                                                          sitk.Euler3DTransform(),
                                                          sitk.CenteredTransformInitializerFilter.GEOMETRY)
    registration_method = sitk.ImageRegistrationMethod()
    registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=250)
    registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
    registration_method.SetMetricSamplingPercentage(0.01)
    registration_method.SetInterpolator(sitk.sitkNearestNeighbor)
    registration_method.SetOptimizerAsGradientDescent(learningRate=3.0, numberOfIterations=10000,
                                                      convergenceMinimumValue=1e-6, convergenceWindowSize=10)

    registration_method.SetOptimizerScalesFromPhysicalShift()
    registration_method.SetInitialTransform(initial_transform, inPlace=False)
    final_transform = registration_method.Execute(sitk.Cast(reference, sitk.sitkFloat32),
                                                 sitk.Cast(image, sitk.sitkFloat32))
    register = sitk.ResampleImageFilter()
    register.SetReferenceImage(reference)
    register.SetInterpolator(sitk.sitkNearestNeighbor)
    register.SetTransform(final_transform)
    ds_register = register.Execute(image)

    return ds_register


def main():

    def mode_selector():
        status = selector.get()
        if not status:
            frame_alpha.tkraise()
            selector.set(True)
        else:
            frame.tkraise()
            selector.set(False)

    def update_slice(self):
        pos = slice_selector.get()
        alpha = alpha_selector.get()
        status = selector.get()
        if not status:
            axs[0].imshow(ds_array[pos,:,:], cmap=plt.cm.get_cmap(colormap.get()))
            axs[1].imshow(phantom_array[pos,:,:], cmap=plt.cm.get_cmap(colormap.get()))
            fig.canvas.draw_idle()
        else:
            ax.imshow(ds_array[pos, :, :], cmap=plt.cm.get_cmap(colormap.get()))
            ax.imshow(phantom_array[pos, :, :], cmap=plt.cm.get_cmap("prism"), alpha=alpha/100)
            fig2.canvas.draw_idle()

        slice_pos = "Nº Slice: " + str(pos)
        label_slice.config(text=slice_pos)

    #Reading RM_Brain_3D-SPGR DICOM
    path_dcm = "data/RM_Brain_3D-SPGR"
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(path_dcm)
    reader.SetFileNames(dicom_names)
    ds = reader.Execute()

    #Reading phantom DICOM
    ds_phantom = sitk.ReadImage('data/icbm_avg_152_t1_tal_nlin_symmetric_VI.dcm')
    phantom_array = sitk.GetArrayFromImage(ds_phantom)  # z, y, x

    #Reading atlas DICOM
    ds_atlas = sitk.ReadImage('data/AAL3_1mm.dcm')

    # Resample Brain DICOM and atlas DICOM to phantom shape

    ds_resample = resample_image(ds, ds_phantom)
    ds_atlas_resample = resample_image(ds_atlas, ds_phantom)

    # Register Brain DICOM and atlas DICOM with phantom

    ds_atlas_register = register_images(ds_atlas_resample, ds_phantom)
    atlas_array = sitk.GetArrayFromImage(ds_atlas_register)  # z, y, x

    ds_register = register_images(ds_resample, ds_phantom)
    ds_array = sitk.GetArrayFromImage(ds_register)  # z, y, x

    # Creating window and frames
    root = tk.Tk()
    root.title("DICOM Image Display")
    top_frame = tk.Frame() # frame with buttons and sliders
    frame = tk.Frame() #frame with synchron visualizator
    frame_alpha = tk.Frame() #frame with alpha visualizator

    top_frame.grid(row = 0, column = 0, sticky = tk.W, columnspan=6)
    frame.grid(row = 1,sticky="nsew", column = 0, columnspan=6)
    frame_alpha.grid(row = 1,sticky="nsew", column = 0, columnspan=6)
    frame.tkraise()

    selector = tk.BooleanVar()

    # Displaying images on synchron visualizator
    fig, axs = plt.subplots(1,2, figsize=(15, 6), dpi=100, sharex=True, sharey=True)
    axs = axs.ravel()
    colormap = tk.StringVar()
    colormap.set("bone")

    axs[0].imshow(ds_array[0,:,:], cmap=plt.cm.get_cmap(colormap.get()))
    axs[1].imshow(phantom_array[0,:,:], cmap=plt.cm.get_cmap(colormap.get()))

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, expand=1)

    toolbar = NavigationToolbar2Tk(canvas, frame)
    toolbar.update()
    canvas.get_tk_widget().pack(side=tk.TOP, expand=1)

    # Displaying images on alpha visualizator
    fig2, ax = plt.subplots(1, figsize=(15, 6), dpi=100, sharex=True, sharey=True)

    alpha = 0
    ax.imshow(ds_array[0, :, :], cmap=plt.cm.get_cmap(colormap.get()))
    ax.imshow(phantom_array[0, :, :], cmap=plt.cm.get_cmap("prism"), alpha=alpha/100)

    canvas_alpha = FigureCanvasTkAgg(fig2, master=frame_alpha)
    canvas_alpha.draw()
    canvas_alpha.get_tk_widget().pack(side=tk.TOP, expand=1)

    toolbar_alpha = NavigationToolbar2Tk(canvas_alpha, frame_alpha)
    toolbar_alpha.update()
    canvas_alpha.get_tk_widget().pack(side=tk.TOP, expand=1)

    # Selecting slices
    pos = 0
    slice_selector = tk.Scale(top_frame, label="Slice selector", from_=0, to=ds_array.shape[0] - 1,
                              orient=tk.HORIZONTAL, length=400,
                              command=update_slice, tickinterval=20)
    slice_selector.pack(side=tk.LEFT, anchor=tk.NW)
    # Showing actual number of slice
    label_slice = tk.Label(top_frame)
    label_slice.pack(side=tk.TOP, anchor=tk.NW, before=slice_selector)
    slice_pos = "Nº Slice: " + str(pos)
    label_slice.config(text=slice_pos)

    # Change between synchron and alhpa visualization
    b = tk.Button(top_frame, text="Mode selector", command=mode_selector, width=10)
    b.pack(side=tk.TOP)

    # Selecting which percentage of alpha use for alpha visualization
    alpha_selector = tk.Scale(top_frame, label="alpha value", from_=0, to=100,
                              orient=tk.HORIZONTAL, length=400,
                              command=update_slice, tickinterval=5)
    alpha_selector.pack(side=tk.TOP)

    root.mainloop()


if __name__ == '__main__':
    main()
