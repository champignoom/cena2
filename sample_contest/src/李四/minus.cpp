#include <iostream>
#include <fstream>
#include <thread>
#include <thread>
#include <vector>
using namespace std;

int main() {
	ifstream fin("minus.in");
	ofstream fout("minus.out");
	cin.rdbuf(fin.rdbuf());
	cout.rdbuf(fout.rdbuf());
	int a, b;
	cin >>a >>b;
	// this_thread::sleep_for(0.2s);
	if (b%2 == 0) {
		cout <<0 <<endl;
	} else if (b%3!=0) {
		if (b%3==1) {
			this_thread::sleep_for(1s);
			cout <<a/(b-b) <<endl;
		} else {
			vector<char> f(1024*1024*200);
			cout <<a-b <<endl;
		}
	} else {
		cout <<a-b <<endl;
	}
}
