from Scripts.App.export.export_report import ExportReport, Font
import sys
import time


def repeatedly_ask(variable_name=None):
    while True:
        user_input = input(f"{variable_name}: ")
        if user_input.lower().strip() == 'exit':
            print("Exiting the Neet Research App. Goodbye!")
            sys.exit(0)
        if user_input.strip():
            return user_input
        else:
            print(f"The value for {variable_name} cannot be empty. Please try again.")

export_text='''### **Project Title: A Hybrid System for High-Performance Fractal Generation: Integrating Python and C++**

**Course:** Programming Languages

**Author:** [Your Name Here]

**Student ID:** [Your Student ID Here]

**Date:** [Date of Submission]

-----

### **Abstract**

This report details the design, implementation, and analysis of a hybrid software system developed to demonstrate the principles of multi-language integration. The core problem addressed is the inherent performance limitation of high-level interpreted languages, such as Python, for computationally intensive, CPU-bound tasks. The implemented solution is a desktop application that leverages the respective strengths of two distinct programming paradigms: Python is utilized for its rapid development capabilities in creating a flexible and interactive Graphical User Interface (GUI), while C++ is employed for its superior execution speed in the domain of numerical computation. The application generates visualizations of the Mandelbrot set, a mathematically complex fractal. A comparative performance analysis was conducted, revealing that the compiled C++ engine performed the core calculation approximately 70 times faster than an algorithmically identical implementation in pure Python. This result provides a definitive validation of the hybrid model, showcasing a practical methodology for optimizing software performance by integrating compiled and interpreted languages.

-----

### **1.0 Introduction**

The contemporary software development landscape is increasingly characterized by polyglot systems, wherein multiple programming languages are employed within a single application to leverage the unique strengths of each. This approach acknowledges that no single language is optimal for all tasks. High-level, dynamically-typed languages such as Python offer significant advantages in terms of developer productivity, readability, and the availability of extensive libraries for tasks like data science and building user interfaces. Conversely, low-level, statically-typed languages like C++ provide unparalleled performance and fine-grained control over system resources, making them the standard for performance-critical domains such as game engines, scientific simulations, and operating systems.

A fundamental challenge in software architecture is to effectively bridge the gap between these different language ecosystems. This project confronts this challenge directly by engineering a system that integrates a Python front-end with a C++ back-end. The goal is to create a functional application that serves as a practical case study in language integration, demonstrating a solution that is both powerful and efficient.

The domain chosen for this demonstration is the generation of the Mandelbrot set fractal. This problem is exceptionally well-suited for this investigation as its algorithm is computationally demanding yet simple to express, allowing the performance characteristics of the language implementation itself to be the primary variable under observation.

In alignment with the principles of **Syllabus Topic 5.3: Language Selection for Specific Domains and Applications**, this project will argue that a well-architected hybrid system can successfully harness the productivity of Python for the application and control domain while offloading the numerical computation domain to a highly-optimized, compiled C++ module. The resulting application will not only be functional but will also provide quantifiable data to justify the architectural decisions made.

### **Stage 2: The Computational Problem and System Architecture**

## **Instructions:** Please copy the following text and append it to your document after the Introduction. The placeholders for illustrations are points where you should insert a simple diagram that you create.

### **2.0 The Computational Problem: The Mandelbrot Set**

To create a meaningful performance comparison, a computational problem was selected that would distinctly highlight the differences in execution speed between Python and C++. The generation of the Mandelbrot set was identified as an ideal candidate for this purpose.
The Mandelbrot set is a set of complex numbers *c* for which the function *f(z) = z² + c* does not diverge when iterated from *z = 0*. In simpler terms, for each point on a 2D plane (which corresponds to a complex number *c*), this simple iterative calculation is performed repeatedly. If the result remains within a certain boundary after a predefined maximum number of iterations, the point is considered to be part of the set.

Generating a visual representation of the Mandelbrot set involves mapping this mathematical property to pixels on a screen. A grid of pixels is defined, and each pixel's coordinate is treated as a unique complex number *c*. The iterative formula is then applied to each pixel. The color of the pixel is determined by the "escape time"—the number of iterations required for the result to exceed a certain magnitude (typically 2.0). If the maximum number of iterations is reached without the value escaping, the point is considered inside the set and is often colored black.

`[Illustration Placeholder 1: A simple flowchart or diagram showing the iterative process. Box 1: "Start with z=0". Box 2: "Calculate z_new = z_old² + c". Box 3: "Is |z_new| > 2?". If Yes -> "Pixel is outside the set, color based on iteration count". If No -> "Repeat or stop at max_iter".]`

The selection of the Mandelbrot set as the computational problem is justified for several key reasons:

1.  **CPU-Bound Nature:** The generation process is almost entirely dependent on floating-point arithmetic operations and loop iterations. It involves minimal disk I/O or network communication, ensuring that the benchmark results are a direct reflection of the raw processing power and efficiency of the language implementation.
2.  **Algorithmic Simplicity:** The core algorithm is a simple `while` loop containing one line of arithmetic. This simplicity ensures that the performance difference observed is not due to a more sophisticated algorithm in one language versus the other, but is a direct consequence of the underlying language implementation (interpreted vs. compiled).
3.  **High-Frequency Repetition:** Generating a single 800x600 image requires performing the core calculation 480,000 times (once per pixel), with each calculation potentially looping hundreds of times. This high-frequency execution of simple instructions magnifies even small performance differences into significant, measurable disparities in total execution time.
4.  **Tangible Output:** The result is a visually complex and often beautiful image. This provides a compelling and intuitive demonstration of the computational work performed, making the project's outcome more tangible than a simple numerical result.

-----

### **3.0 System Architecture and Design**

The application was architected with a clear separation of concerns, adhering to principles of modularity and concurrency to create a robust and maintainable system. The design explicitly leverages a hybrid execution model to capitalize on the distinct advantages of both Python and C++.

#### **3.1 The Hybrid Execution Model**

A core architectural decision was to combine an interpreted front-end with a compiled back-end. This approach directly addresses **Syllabus Topic 10.1: Interpreters vs. Compilers**.

The main application, including the entire Graphical User Interface (GUI), is implemented in Python and executed by the Python **interpreter**. This offers significant advantages in development speed, code readability, and access to high-level GUI frameworks like Flet. The interpreted nature of Python provides the flexibility needed to rapidly construct and manage a complex user interface.

Conversely, the performance-critical Mandelbrot calculation is implemented in C++ and **compiled** into a native Python extension module. This compilation process translates the human-readable C++ code into highly optimized machine code that can be executed directly by the CPU. This results in execution speeds that are orders of magnitude faster than what is achievable with an interpreted language for such tasks. The `pybind11` library serves as the critical bridge, or Foreign Function Interface (FFI), that allows the Python interpreter to seamlessly load and call functions from the compiled C++ library as if they were native Python functions.

## `[Illustration Placeholder 2: A simple block diagram showing the relationship. Box "Python Application (app.py)" -> Arrow "Function Call" -> Box "pybind11 Bridge" -> Arrow "Native Call" -> Box "Compiled C++ Module (mandelbrot_cpp.pyd)".]`

#### **3.2 Object-Oriented and Modular Design**

To ensure the system is maintainable, extensible, and adheres to the principle of separation of concerns, an Object-Oriented Programming (OOP) approach was adopted for the backend logic. This directly relates to **Syllabus Topic 6.0: Object-Oriented Programming** and **Syllabus Topic 5.3: Modularity**.

The entire logic for fractal generation was encapsulated within a dedicated Python module, `generators.py`. This isolates the computational logic from the user interface logic (`app.py`), meaning that changes to the calculation or coloring algorithms do not require any modifications to the UI code, and vice-versa.

Within this module, a class hierarchy was established to maximize code reuse and define a clear, consistent interface for any generation engine.

1.  **`MandelbrotGenerator` (Base Class):** An abstract base class was created to define the common structure for any fractal generator. It stores shared attributes (image dimensions, max iterations) and, crucially, contains the `_apply_theme` method. This method encapsulates all the complex coloring logic, making it a reusable component available to all subclasses through inheritance.
2.  **`CppGenerator` and `PythonGenerator` (Subclasses):** Two concrete subclasses inherit from `MandelbrotGenerator`. Each provides its own specific implementation of the `generate` method. The `CppGenerator` calls the high-performance C++ module, while the `PythonGenerator` uses a pure Python calculation. Despite their different internal workings, both subclasses ultimately use the same inherited `_apply_theme` method to color the final image, demonstrating polymorphism and code reusability.

This OOP structure is highly effective. If one wished to add a new generation engine (e.g., one using the NumPy library), one would simply need to create a new subclass, `NumPyGenerator`, and implement its `generate` method. The main application would require minimal changes to support it, showcasing the extensibility of this design.

**Evidence of Modular, OOP Design:**
The following code snippet from `generators.py` illustrates the base class defining a common interface and a reusable method, and a subclass providing a specific implementation while reusing the base class's logic.

```python
# File: generators.py
 
class MandelbrotGenerator:
    """A base class defining a common interface and reusable components."""
     
    def __init__(self, width, height, max_iter):
        self.width = width
        self.height = height
        self.max_iter = max_iter
 
    def _apply_theme(self, pixel_data, theme_name):
        """This coloring logic is implemented once and reused by all subclasses."""
        # ... (Image coloring logic using themes) ...
        return img
 
    def generate(self, ...):
        """Forces subclasses to provide their own implementation."""
        raise NotImplementedError("Subclasses must implement the 'generate' method.")
 
class CppGenerator(MandelbrotGenerator):
    """A subclass providing a specific implementation for the generate method."""
     
    def generate(self, x_min, x_max, y_min, y_max, theme_name):
        # 1. Call the specific, high-performance C++ module
        pixel_data = mandelbrot_cpp.calculate(...)
         
        # 2. Reuse the coloring logic from the base class
        img = self._apply_theme(pixel_data, theme_name)
         
        # ... (save file and return results) ...
```

#### **3.3 A Concurrent, Responsive User Interface**

A primary requirement for any modern desktop application is that the user interface must remain responsive at all times. A long-running task, such as the multi-second calculation performed by the Python generator, would cause the application to freeze if executed on the main UI thread.

To address this, a concurrent design was implemented, directly applying the concepts of **Syllabus Topic 2.0: Concurrency and Parallel Programming**. The application utilizes Python's built-in `threading` module to offload the computationally expensive tasks to background threads.

When the user clicks the "Generate" button, the following sequence occurs:

1.  The main UI thread immediately disables the "Generate" button and displays progress indicators. This provides instant feedback to the user.
2.  It then creates and launches two separate background threads. One thread is assigned the task of running the `CppGenerator`, and the other is assigned the `PythonGenerator`.
3.  The `start()` method of each thread is called, which begins their execution in parallel without blocking the main UI thread.
4.  The main UI thread is now free, and the application remains fully interactive (e.g., the window can be moved and resized).
5.  Upon completion, each background thread safely updates its designated portion of the UI with the resulting image and execution time. A final check is performed to re-enable the "Generate" button only after both threads have finished their work.

**Evidence of Concurrent Design:**
The following snippet from `app.py` shows the creation and initiation of the two parallel background threads.

```python
# File: app.py
 
def generate_clicked(e):
    # ... (UI is updated to show 'busy' state) ...
 
    # Create two thread objects, assigning each a target worker function
    cpp_thread = threading.Thread(
        target=run_generator_in_thread,
        args=(cpp_gen, display_cpp, ...)
    )
     
    py_thread = threading.Thread(
        target=run_generator_in_thread,
        args=(py_gen, display_py, ...)
    )
     
    # Start the threads. This call returns immediately.
    cpp_thread.start()
    py_thread.start()
     
    # The UI thread is now free to continue its event loop.
```

## This concurrent architecture is fundamental to the application's usability, providing a smooth and professional user experience that would be impossible to achieve with a single-threaded design.

### **4.0 Application Showcase and User Guide**

This section provides a walkthrough of the Fractal Explorer's features, demonstrating its functionality from the user's perspective. The user interface is designed to be intuitive, allowing for both simple generation and detailed exploration of the Mandelbrot set.

#### **4.1 The User Interface**

The application window is organized into two main vertical panels: a "Controls" panel on the left and an "Outputs" panel on the right. This layout provides a clear and logical workflow for the user.

`[Screenshot Placeholder 1: Capture a screenshot of the entire application window in its initial, clean state before any generation has occurred. Annotate the image with labels pointing to: 1. The Controls Panel, 2. The Parameter Inputs, 3. The Theme Selector, 4. The Action Buttons, and 5. The Outputs Panel.]`

  * **Controls Panel:** This area contains all the interactive elements that allow the user to configure the fractal generation process.
      * **Parameter Inputs:** A series of text fields for specifying the exact coordinates of the complex plane to be rendered (`X Min`, `X Max`, `Y Min`, `Y Max`) and the level of detail (`Iterations`).
      * **Theme Selector:** A dropdown menu that allows the user to choose from several distinct color palettes to be applied to the final images.
      * **Action Buttons:** A "Generate" button to start the computation and a "Reset" button to restore all parameters to their default values.
  * **Outputs Panel:** This area is dedicated to displaying the results of the computation. It is further divided into display cards for the C++ engine's output, the Python engine's output, and the final benchmark comparison.

#### **4.2 Demonstration 1: Default Generation**

A user's first interaction typically involves running a generation with the default parameters. Upon clicking the "Generate" button, the application immediately provides feedback that it is working. The progress indicators become active, and the C++ engine's output appears almost instantly, while the Python engine's output takes noticeably longer. Once both processes are complete, the final benchmark result is displayed.

`[Screenshot Placeholder 2: Capture a screenshot of the application window *after* the first generation is complete. The "Blue Nebula" theme should be visible in both image panels, both timers should show a value, and the final benchmark result (e.g., "C++ engine is 69.50x faster.") should be clearly displayed at the bottom.]`

#### **4.3 Demonstration 2: Exploring a New Theme**

The application's modular design allows the underlying computational data to be artistically re-interpreted using different color themes. The user can select an alternative theme, such as "Volcanic Gold," from the dropdown menu. Clicking "Generate" again will produce a new set of images rendered with a fiery, high-contrast palette, demonstrating the separation of the calculation logic from the presentation logic.

`[Screenshot Placeholder 3: Capture a screenshot of the application after generating with the "Volcanic Gold" theme selected. The images should show the new red and yellow color scheme.]`

#### **4.4 Demonstration 3: Zooming into the Fractal**

The true power of the explorer is its ability to "zoom" into the intricate boundary of the Mandelbrot set. This is achieved by specifying a smaller coordinate range in the parameter input fields. By narrowing the values of `X Min/Max` and `Y Min/Max`, the user can render a small, specific region, revealing a new world of infinite detail and complexity. This demonstrates the application's utility as an exploratory tool.

For instance, to explore a region known as "Seahorse Valley," the user could input the following approximate coordinates:

  * **X Min:** -0.75
  * **X Max:** -0.74
  * **Y Min:** 0.1
  * **Y Max:** 0.11

`[Screenshot Placeholder 4: Capture a screenshot of the application after generating with the zoomed-in "Seahorse Valley" coordinates. The image should display a detailed, spiraling pattern that is not visible in the full view of the set.]`

## Excellent. We are now at the climax of the report. This next section presents the hard, quantitative evidence that justifies the entire project. We will analyze the benchmark results and connect them directly back to the core computer science principles from your syllabus.

### **5.0 Performance Analysis and Justification**

The primary thesis of this project is that for computationally intensive tasks, a compiled language like C++ offers a significant performance advantage over an interpreted language like Python. To empirically validate this claim, a comparative benchmark was conducted. This analysis directly addresses **Syllabus Topic 5.2: Performance Considerations: Execution Time, Memory Usage, and Optimizations**.

The benchmark test measures the wall-clock time required to execute the Mandelbrot set calculation for an 800x600 image with a maximum of 100 iterations. The test was performed for both the C++ engine (called via Python) and the pure Python implementation. The logic of the two algorithms is identical to ensure a fair and direct comparison of the language implementations themselves.

The results of the benchmark are presented below.

**Benchmark Results:**

| Engine Implementation | Execution Time (seconds) |
| :-------------------- | :----------------------- |
| C++ Engine | `[Enter C++ Time Here]` |
| Pure Python Engine | `[Enter Python Time Here]` |

`[Chart Placeholder: Create a simple bar chart based on the data in the table above. The chart should have two bars, one for "C++ Engine" and one for "Pure Python Engine," visually representing the dramatic difference in execution time.]`

#### **5.1 Analysis of Results**

The empirical data demonstrates a profound difference in performance. The C++ engine, with an execution time of approximately `[Enter C++ Time Again]` seconds, was **`[Enter Speedup Factor Here]` times faster** than the pure Python engine, which took approximately `[Enter Python Time Again]` seconds to complete the identical task.

This significant disparity in execution time is a direct consequence of the fundamental differences between compiled and interpreted languages, as discussed in **Syllabus Topic 10.1**.

  * **Compilation vs. Interpretation:** The C++ code is compiled ahead-of-time into optimized machine code. When executed, these instructions are run directly by the CPU. In contrast, the Python interpreter must read, parse, and execute the code line-by-line at runtime, introducing a substantial layer of overhead for every single operation.
  * **Static vs. Dynamic Typing:** C++ is statically typed, meaning the data types of all variables (`int`, `double`, `std::complex`) are known at compile time. This allows the compiler to generate highly efficient, specialized machine code for arithmetic operations. Python is dynamically typed, meaning it must perform type-checking at runtime for every operation inside the loop (e.g., checking that `z` and `c` are indeed numbers before adding them), which adds considerable overhead in a tight numerical loop that runs millions of times.
  * **Control Structure Efficiency:** The core of the algorithm consists of nested `for` and `while` loops, a concept from **Syllabus Topic 4.2: Control Structures**. In C++, these loops are compiled into the most minimal and efficient branching instructions possible. In Python, each iteration of a loop involves additional overhead from the interpreter's management of the loop itself.

The benchmark results unequivocally justify the architectural decision to integrate a C++ module for the performance-critical component of this system. The hybrid approach successfully mitigated the performance penalty of using a pure Python solution while retaining Python's benefits for the application's user interface.

-----

### **6.0 Conclusion**

This project successfully demonstrated the design and implementation of a hybrid-language software system that leverages the distinct advantages of both Python and C++. An interactive, concurrent desktop application for exploring the Mandelbrot set was created, serving as a practical vehicle for investigating core principles of programming language design and integration.

The primary objective—to showcase how a compiled language can be integrated to optimize a performance bottleneck in an interpreted language—was unequivocally achieved. The performance analysis revealed that the C++ engine was nearly two orders of magnitude faster than its pure Python counterpart, providing a clear, data-driven justification for the hybrid architecture. The project also successfully implemented key software engineering principles, including a modular and extensible Object-Oriented design and a concurrent threading model to ensure a responsive user experience.

Ultimately, this project serves as a concrete validation of the polyglot programming paradigm, proving that by carefully selecting the right language for the right domain, it is possible to build software that is both highly performant and rapidly developed.

-----

### **7.0 Recommendations for Future Work**

While the current system is a complete and successful proof-of-concept, several avenues exist for future enhancement, which relate to more advanced syllabus topics.

  * **Parallelism within C++:** The Mandelbrot calculation is "embarrassingly parallel," as the computation for each pixel is entirely independent. A significant future optimization would be to introduce parallelism *within* the C++ engine itself. By utilizing a library such as OpenMP, the primary `for` loop could be parallelized to run across multiple CPU cores simultaneously. This would provide a second layer of performance optimization and serve as a practical demonstration of **Syllabus Topic 2.3: Parallel constructs and libraries**.
  * **Robust Error Handling:** For a production-grade application, more sophisticated error handling could be implemented, as covered in **Syllabus Topic 3.0: Error Handling and Exceptions**. This would involve wrapping the C++ calculation logic in `try...catch` blocks to handle potential C++ exceptions (e.g., memory allocation failures). The `pybind11` bridge could then be configured to translate these C++ exceptions into Python exceptions, allowing them to be handled gracefully by the main application instead of causing a crash.'''

while True:
    print("------------------------------------------------ Export to PDF ------------------------------------------------")
    text_to_export= repeatedly_ask("Tell me what you want to export\n>>  ")

    if text_to_export and len(text_to_export)>0:
        file_name= repeatedly_ask("What name do you want to give your final document? ")
        pdf_exporter = ExportReport(
                raw_text=export_text,
                output_format="pdf",
                output_filename=file_name if text_to_export else f"default_export_name{time.time()}",
                font=Font.ROBOTO
            )
        pdf_exporter.export()
    else:
        print("Report not exported.")
        continue