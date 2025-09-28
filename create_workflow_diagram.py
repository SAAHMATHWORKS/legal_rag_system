from graphviz import Digraph
import os

def create_langgraph_image(output_filename="langgraph_workflow", format="png"):
    """
    Create a PNG image of the LangGraph workflow
    """
    # Create a new directed graph
    dot = Digraph(comment='LangGraph Workflow', format=format)
    dot.attr(rankdir='TB', size='8,10')  # Top to bottom layout
    
    # Define node styles
    dot.attr('node', shape='rectangle', style='rounded,filled', 
             fillcolor='lightblue', fontname='Arial', fontsize='12')
    
    # Define special nodes
    dot.attr('node', shape='ellipse', fillcolor='lightgreen')  # Start/End nodes
    
    # Add nodes
    dot.node('START', 'START', fillcolor='lightgreen')
    dot.node('END', 'END', fillcolor='lightgreen')
    
    # Regular nodes with different colors for different types
    dot.node('router', 'Router\n(Country Detection)', fillcolor='lightcoral')
    dot.node('benin_retrieval', 'Benin Retrieval', fillcolor='lightyellow')
    dot.node('madagascar_retrieval', 'Madagascar Retrieval', fillcolor='lightyellow')
    dot.node('unclear_route', 'Unclear Route', fillcolor='lightyellow')
    dot.node('detect_assistance', 'Detect Assistance\nNeeded?', fillcolor='orange')
    dot.node('response_generation', 'Response Generation', fillcolor='lightblue')
    dot.node('collect_email', 'Collect Email', fillcolor='lightpink')
    dot.node('process_assistance', 'Process Assistance', fillcolor='lightpink')
    
    # Add edges with different styles for conditional vs regular edges
    dot.edge('START', 'router')
    
    # Conditional edges from router (dashed for conditional)
    dot.edge('router', 'benin_retrieval', label=' Benin', style='dashed')
    dot.edge('router', 'madagascar_retrieval', label=' Madagascar', style='dashed')
    dot.edge('router', 'unclear_route', label=' Unclear', style='dashed')
    
    # Regular edges from retrieval nodes
    dot.edge('benin_retrieval', 'detect_assistance')
    dot.edge('madagascar_retrieval', 'detect_assistance')
    dot.edge('unclear_route', 'detect_assistance')
    
    # Conditional edges from detect_assistance
    dot.edge('detect_assistance', 'collect_email', label=' Assistance\nNeeded', style='dashed')
    dot.edge('detect_assistance', 'response_generation', label=' No Assistance', style='dashed')
    
    # Assistance flow
    dot.edge('collect_email', 'process_assistance')
    dot.edge('process_assistance', 'END')
    
    # Normal flow
    dot.edge('response_generation', 'END')
    
    # Add some styling for better visualization
    dot.attr(label='Multi-Country Legal Assistant Workflow')
    dot.attr(fontsize='16', fontname='Arial Bold')
    
    # Render the graph
    dot.render(output_filename, cleanup=True, format=format)
    print(f"Workflow image saved as {output_filename}.{format}")
    
    return dot

def create_detailed_langgraph_image(output_filename="langgraph_workflow_detailed", format="png"):
    """
    Create a more detailed version with function names
    """
    dot = Digraph(comment='Detailed LangGraph Workflow', format=format)
    dot.attr(rankdir='TB', size='10,12')
    
    # Node styles
    dot.attr('node', shape='rectangle', style='rounded,filled', 
             fillcolor='lightblue', fontname='Arial', fontsize='10')
    
    # Special nodes
    dot.attr('node', shape='ellipse', fillcolor='lightgreen')
    dot.node('START', 'START')
    dot.node('END', 'END')
    
    # Detailed nodes with function names
    dot.attr('node', fillcolor='lightcoral')
    dot.node('router', 'router\n_router_node')
    
    dot.attr('node', fillcolor='lightyellow')
    dot.node('benin_retrieval', 'benin_retrieval\n_benin_retrieval_node')
    dot.node('madagascar_retrieval', 'madagascar_retrieval\n_madagascar_retrieval_node')
    dot.node('unclear_route', 'unclear_route\n_unclear_route_node')
    
    dot.attr('node', fillcolor='orange')
    dot.node('detect_assistance', 'detect_assistance\n_detect_assistance_node')
    
    dot.attr('node', fillcolor='lightblue')
    dot.node('response_generation', 'response_generation\n_response_generation_node')
    
    dot.attr('node', fillcolor='lightpink')
    dot.node('collect_email', 'collect_email\n_collect_email_node')
    dot.node('process_assistance', 'process_assistance\n_process_assistance_node')
    
    # Edges (same structure as before)
    dot.edge('START', 'router')
    dot.edge('router', 'benin_retrieval', label=' Benin', style='dashed')
    dot.edge('router', 'madagascar_retrieval', label=' Madagascar', style='dashed')
    dot.edge('router', 'unclear_route', label=' Unclear', style='dashed')
    dot.edge('benin_retrieval', 'detect_assistance')
    dot.edge('madagascar_retrieval', 'detect_assistance')
    dot.edge('unclear_route', 'detect_assistance')
    dot.edge('detect_assistance', 'collect_email', label=' Assistance', style='dashed')
    dot.edge('detect_assistance', 'response_generation', label=' No Assistance', style='dashed')
    dot.edge('collect_email', 'process_assistance')
    dot.edge('process_assistance', 'END')
    dot.edge('response_generation', 'END')
    
    dot.render(output_filename, cleanup=True, format=format)
    print(f"Detailed workflow image saved as {output_filename}.{format}")
    
    return dot

if __name__ == "__main__":
    # Install required package: pip install graphviz
    
    try:
        # Create basic workflow image
        create_langgraph_image("legal_assistant_workflow")
        
        # Create detailed version
        create_detailed_langgraph_image("legal_assistant_workflow_detailed")
        
        print("Workflow images created successfully!")
        print("Files generated:")
        print("- legal_assistant_workflow.png")
        print("- legal_assistant_workflow_detailed.png")
        
    except Exception as e:
        print(f"Error creating workflow image: {e}")
        print("Make sure you have Graphviz installed:")
        print("1. Install graphviz Python package: pip install graphviz")
        print("2. Install Graphviz system package:")
        print("   - Windows: Download from https://graphviz.org/download/")
        print("   - macOS: brew install graphviz")
        print("   - Linux: sudo apt-get install graphviz")