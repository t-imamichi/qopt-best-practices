# %%
from qiskit.circuit.library import QAOAAnsatz
from qiskit.quantum_info import SparsePauliOp
from qiskit_optimization import QuadraticProgram
from qiskit.transpiler import Layout
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit import qpy

# %%
problem = QuadraticProgram()
if True:
    problem.read_from_lp_file("../demos/qiskit_patterns/data/125node_example.lp")
else:
    problem.binary_var_list(10)
    problem.minimize(quadratic={(0, 1): 1, (1, 2): 2, (2, 3): 3, (3, 4): 4})
print(problem.prettyprint())
# %%
hamiltonian, offset = problem.to_ising()
lst = sorted(hamiltonian.to_list())
# FakeKawasaki has a faulty edge in the following operator
# lst = lst[31:32]
lst2 = lst[::2] + lst[1::2]
hamiltonian = SparsePauliOp.from_list(lst2)
# %%
service = QiskitRuntimeService()
backend_name = "ibm_kawasaki"
backend = service.get_backend(backend_name)
#backend = service.get_backend("ibm_kawasaki")
# backend = FakeOsaka()
# backend = FakeKawasaki()
# the demo uses all qubits except two corner qubits (13 and 113) of eagle
qubits = sorted(set(range(127)) - {13, 113})[: hamiltonian.num_qubits]

# %%
title = ["zero", "one"]
for reps in [0, 1]:
    qaoa_circ = QAOAAnsatz(hamiltonian, reps=reps)
    qaoa_circ.measure_all()
    # _ = qaoa_circ.decompose(reps=3).draw("mpl", fold=False, filename="init.png", scale=0.5)

    # %%
    initial_layout = Layout.from_intlist(qubits, qaoa_circ.qregs[0])  # needs qaoa_circ
    # %%
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=1,
        initial_layout=initial_layout,
        layout_method="trivial",
    )
    opt_circ = pm.run(qaoa_circ)
    # %%
    _ = opt_circ.draw("mpl", filename=f"final_{backend_name}_{title[reps]}.png", scale=1.0, fold=False)

    # %%
    with open(f"125node_{backend_name}_depth_{title[reps]}.qpy", "wb") as file:
        qpy.dump(opt_circ, file)
