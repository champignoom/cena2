#include <iostream>
#include <thread>
#include <chrono>
#include <fstream>
using namespace std;

int main() {
	ifstream fin("times.in");
	ofstream fout("times.out");
	cin.rdbuf(fin.rdbuf());
	cout.rdbuf(fout.rdbuf());

	int a, b;
	cin >>a >>b;
	// this_thread::sleep_for(0.5s);
	cout <<a*b <<endl;
}
